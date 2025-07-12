
from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.conf import settings
from openai import OpenAI
from restaurante.models import (
    Booking, Order, OrderItem, CustomerReview, UserProfile,
    Category, MenuItem
)

client = OpenAI(api_key=settings.OPENAI_API_KEY)


# -------------------------------
# 🔥 Static restaurant context
# -------------------------------
MENU_STATIC_CONTEXT = None

from restaurante.models import Category, MenuItem, Booking, Order

# Your TIME_SLOTS and DELIVERY_TIME_SLOTS imported from the same module
from restaurante.models import TIME_SLOTS, DELIVERY_TIME_SLOTS

MENU_STATIC_CONTEXT = None

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

    # Add explicit time slots info from your model definitions
    booking_slots = [f"{slot[0]}" for slot in Booking._meta.get_field('reservation_time').choices[:5]]
    booking_slots_str = ", ".join(booking_slots)

    delivery_slots = ", ".join([slot[0] for slot in DELIVERY_TIME_SLOTS])
    delivery_types = ", ".join([choice[0] for choice in Order._meta.get_field('delivery_type').choices])
    payment_methods = ", ".join([choice[0] for choice in Order._meta.get_field('payment_method').choices])

    MENU_STATIC_CONTEXT = f"""
OUR MENU CATEGORIES:
{category_str}

FEATURED SPECIALS:
{specials_context}

FULL MENU ITEMS:
{menu_context}

RESERVATION TIME SLOTS (sample first 5):
{booking_slots_str}

DELIVERY TIME SLOTS:
{delivery_slots}

DELIVERY OR PICKUP OPTIONS:
{delivery_types}

PAYMENT METHODS AVAILABLE:
{payment_methods}

Note: You can pay using Stripe or opt for Cash on Delivery.
We deliver or you can pick up — your choice. Flexible time slots from 11:00 AM to 8:00 PM every half hour, plus ASAP delivery if you're super hungry!
"""
    return MENU_STATIC_CONTEXT



# -------------------------------
# 🔥 Dynamic user context (bookings, orders, reviews)
# -------------------------------
from datetime import date

def get_address_label(user):
    try:
        profile = user.profile
        dob = profile.dob
        gender = profile.gender
    except (AttributeError, UserProfile.DoesNotExist):
        return "mitra"

    # Compute age
    age = None
    if dob:
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    if gender == "M":
        if age is not None:
            return "bhaiya" if age < 40 else "chacha"
        return "bhaiya"
    elif gender == "F":
        if age is not None:
            if age < 30:
                return "bahini"
            elif age < 50:
                return "didi"
            else:
                return "mataji"
        return "didi"
    else:
        return "mitra"


def get_user_context(user):
    if not user.is_authenticated:
        return "No user is logged in, so bas aam taur pe madad karo."

    address_as = get_address_label(user)

    # Profile
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

    # Recent bookings
    bookings = Booking.objects.filter(user=user).order_by("-reservation_date")[:3]
    booking_str = "\n".join([
        f"{b.reservation_date} at {b.reservation_time} ({b.no_of_guests} guests, occasion: {b.occasion}, Ref: {b.reference_number})"
        for b in bookings
    ]) or "No recent bookings."

    # Recent orders
    orders = Order.objects.filter(user=user).order_by("-date")[:3]
    order_str = ""
    for o in orders:
        items = OrderItem.objects.filter(order=o)
        item_list = ", ".join([f"{i.menuitem.title} x{i.quantity}" for i in items])
        order_str += f"\nOrder #{o.id} on {o.date}: {item_list} | Total: ${o.total} | Status: {'Delivered' if o.status else 'Pending'}"
    order_str = order_str or "No recent orders."

    # Recent reviews
    reviews = CustomerReview.objects.filter(user=user).order_by("-created_at")[:3]
    review_str = "\n".join([f"{r.feedback[:60]}... (⭐ {r.rating})" for r in reviews]) or "No recent reviews."

    return f"""
👋 TOH KA HO {address_as.upper()} {user.username}, sab theek ba? 
Aapke liye humne niche sab details jama kiya hai — dekhiye zara:

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
# 🔥 Main view: no memory, but split
# -------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def chaatgpt_view(request):
    user = request.user
    message = request.data.get("message", "").strip()

    static_context = get_static_menu_context()
    user_context = get_user_context(user)

    context = f"""
You are चाटGPT, a witty Indian street food assistant. 
Respond in an Eastern UP Benarasi-Awadhi style. 
Try to intersperse your conversation with a streetfood joke with 1/4 frequency,
but be serious if the user asks a specific question.

{user_context}

{static_context}
"""

    messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": message}
    ]

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

    return StreamingHttpResponse(stream_generator(), content_type='text/plain')
