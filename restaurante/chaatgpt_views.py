


from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.core.cache import cache
from django.conf import settings
from openai import OpenAI
from restaurante.models import Booking, Order, OrderItem, CustomerReview, UserProfile, Category, MenuItem
from restaurante.models import TIME_SLOTS, DELIVERY_TIME_SLOTS
from datetime import datetime
from datetime import date

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# -------------------------------
# Address helper
def get_address_label(user):
    try:
        profile = user.profile
        dob = profile.dob
        gender = profile.gender
    except (AttributeError, UserProfile.DoesNotExist):
        return "mitra"

    age = None
    if dob:
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    if gender == "M":
        return "bhaiya" if age is None or age < 40 else "chacha"
    elif gender == "F":
        if age is None:
            return "didi"
        if age < 30:
            return "bahini"
        elif age < 50:
            return "didi"
        else:
            return "mataji"
    return "mitra"

# -------------------------------
# Static restaurant context
MENU_STATIC_CONTEXT = None

def format_slot(slot):
    # converts "13:30" -> "1:30 PM"
    return datetime.strptime(slot, "%H:%M").strftime("%-I:%M %p")

def get_static_menu_context():
    global MENU_STATIC_CONTEXT
    if MENU_STATIC_CONTEXT:
        return MENU_STATIC_CONTEXT

    categories = Category.objects.all()
    category_str = ", ".join([c.title for c in categories]) or "No categories."

    menu_items = MenuItem.objects.all()
    menu_context = "\n".join([
        f"{item.title} (${item.price}) - {item.description or 'No description'}"
        for item in menu_items
    ]) or "No menu data."

    specials = MenuItem.objects.filter(featured=True)
    specials_context = "\n".join([
        f"{item.title} (${item.price}) - {item.description or 'No description'}"
        for item in specials
    ]) or "No specials."

    booking_slots = ", ".join([format_slot(slot[0]) for slot in TIME_SLOTS])
    delivery_slots = ", ".join([slot[0] if slot[0] == "ASAP" else format_slot(slot[0]) for slot in DELIVERY_TIME_SLOTS])
    delivery_types = ", ".join([choice[0] for choice in Order._meta.get_field('delivery_type').choices])
    payment_methods = ", ".join([choice[0] for choice in Order._meta.get_field('payment_method').choices])

    MENU_STATIC_CONTEXT = f"""
🍽️ OUR MENU CATEGORIES:
{category_str}

🌟 FEATURED SPECIALS:
{specials_context}

📜 FULL MENU ITEMS:
{menu_context}

⌚ RESERVATION TIME SLOTS (throughout the day):
{booking_slots}

🚚 DELIVERY TIME SLOTS:
{delivery_slots}

📝 HOW TO ORDER OR BOOK:
- You can place a table booking directly on our website. An email confirmation with all your details will be sent to you right away.
- Similarly, place your food order online. Once confirmed, you’ll also receive an email with the order summary and expected delivery/pickup time.

💰 PAYMENT & DELIVERY OPTIONS:
- We accept payments via Stripe (card) or Cash on Delivery.
- We offer both pickup and delivery options. Just select what you prefer at checkout!

✅ Note: All our slots run from 11:00 AM till 8:00 PM every half hour, plus we have an ASAP option for quick delivery if you're hungry right now!
"""
    return MENU_STATIC_CONTEXT

# -------------------------------
# User profile context
def get_user_context(user):
    if not user.is_authenticated:
        return "No user is logged in, so bas aam taur pe madad karo."

    address_as = get_address_label(user)

    try:
        profile = user.profile
        profile_str = f"""
- DOB: {profile.dob}
- Gender: {profile.get_gender_display()}
- City: {profile.city}, State: {profile.state}, Country: {profile.country}
- Marital Status: {profile.get_marital_status_display()}
- Education: {profile.get_education_display()}
- Income: {profile.get_income_display()}
- Phone: {profile.phone}
"""
    except (AttributeError, UserProfile.DoesNotExist):
        profile_str = "No profile data available."

    bookings = Booking.objects.filter(user=user).order_by("-reservation_date")[:3]

    booking_str = "\n".join([
        f"{b.reservation_date.strftime('%B %d, %Y')} at {format_slot(b.reservation_time)} "
        f"({b.no_of_guests} guests, occasion: {b.occasion}, Ref: {b.reference_number})"
        for b in bookings
    ]) or "No recent bookings."

    orders = Order.objects.filter(user=user).order_by("-date")[:3]
    order_str = ""
    for o in orders:
        items = OrderItem.objects.filter(order=o)
        item_list = ", ".join([f"{i.menuitem.title} x{i.quantity}" for i in items])
        order_str += (
            f"\nOrder #{o.id} on {o.date.strftime('%B %d, %Y')}: {item_list} "
            f"| Total: ${o.total} | Status: {'Delivered' if o.status else 'Pending'}"
        )
    order_str = order_str or "No recent orders."

    reviews = CustomerReview.objects.filter(user=user).order_by("-created_at")[:3]
    review_str = "\n".join([f"{r.feedback[:60]}... (⭐ {r.rating})" for r in reviews]) or "No recent reviews."

    return f"""
KA HO {user.username} {address_as.upper()}, sab theek ba?

USER INFO:
- Username: {user.username}
- Addressed as: {address_as}
- Email: {user.email}
- Profile Details: {profile_str}

RECENT BOOKINGS:
{booking_str}

RECENT ORDERS:
{order_str}

RECENT REVIEWS:
{review_str}
"""

# -------------------------------
# Cache history
def get_chat_history(user, session_id, limit=8):
    key = f"chat_history_user_{user.id}" if user and user.is_authenticated else f"chat_history_guest_{session_id}"
    history = cache.get(key, [])
    return history[-limit:]

def save_chat_turn(user, session_id, role, message):
    key = f"chat_history_user_{user.id}" if user and user.is_authenticated else f"chat_history_guest_{session_id}"
    history = cache.get(key, [])
    history.append({"role": role, "content": message})
    cache.set(key, history, timeout=600)  # 10 min cache

# -------------------------------
# Main view with Redis memory
@api_view(["POST"])
@permission_classes([AllowAny])
def chaatgpt_view(request):
    user = request.user
    message = request.data.get("message", "").strip()
    session_id = request.COOKIES.get('chat_session_id') or request.data.get('session_id')

    static_context = get_static_menu_context()
    user_context = get_user_context(user)

    history_messages = get_chat_history(user, session_id, limit=6)


    messages = [
        {
            "role": "system",
            "content": f"""
    You are चाटGPT, ek witty Indian street food assistant.
    Your style is Eastern UP Benarasi-Awadhi Hinglish with light street food jokes (approx 25% frequency), but always serious and specific when user asks about booking, ordering, delivery, or payments.

    ✅ Rules for personalization:
    - ONLY greet the user by name and optionally ask about the weather in their city the **first time in the session**. Do not repeat this greeting or weather question again in the same chat.
    - After that, use normal friendly Hinglish without repeatedly using the user's name.

    ✅ Always remember to clarify in responses related to booking or ordering:
    - Bookings and food orders must be placed on the website. The user will receive an email confirmation immediately.
    - Payments can be made via Stripe (card) or Cash on Delivery.
    - Delivery and pickup are both available. Delivery slots run every half hour from 11:00 AM to 8:00 PM, plus there's an ASAP option.

    Use the user info and static context provided below to personalize only at the start, then keep conversations casual.

    Below is the detailed restaurant context and user info:

    {user_context}

    {static_context}
    """
        }] + history_messages + [{"role": "user", "content": message}]

    def stream_generator():
        assistant_reply = ""
        try:
            stream = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.6,
                stream=True
            )
            for chunk in stream:
                delta = getattr(chunk.choices[0].delta, "content", None)
                if delta:
                    assistant_reply += delta
                    yield delta
        except Exception as e:
            print(f"Streaming error: {e}")
            yield "Sorry, something went wrong."
        finally:
            save_chat_turn(user, session_id, "user", message)
            save_chat_turn(user, session_id, "assistant", assistant_reply)

    return StreamingHttpResponse(stream_generator(), content_type='text/plain')
