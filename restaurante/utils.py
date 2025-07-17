from datetime import date
from django.core.cache import cache
from restaurante.models import (
    ChatHistory,
    Booking,
    Order,
    OrderItem,
    CustomerReview,
    UserProfile
)
from datetime import datetime, date

def format_slot(slot):
    # converts "13:30" -> "1:30 PM"
    return datetime.strptime(slot, "%H:%M").strftime("%-I:%M %p")
# -------------------------------
# Chat history helpers
# def get_chat_history(user, session_id, limit=8):
#     key = f"chat_history_user_{user.id}" if user and user.is_authenticated else f"chat_history_guest_{session_id}"
#     history = cache.get(key, [])
#     return history[-limit:]

# def save_chat_turn(user, session_id, role=None, message=None, full_message=None):
#     key = f"chat_history_user_{user.id}" if user and user.is_authenticated else f"chat_history_guest_{session_id}"
#     history = cache.get(key, [])
#     if full_message:
#         history.append(full_message)
#     else:
#         history.append({"role": role, "content": message})
#     cache.set(key, history, timeout=600)

def get_chat_history(user, session_id, limit=8):
    """
    Retrieves last `limit` messages from cache. Each message is a dict like:
    {"role": "user", "content": "..."} or
    {"role": "function", "name": "...", "content": "..."}
    """
    key = f"chat_history_user_{user.id}" if user and user.is_authenticated else f"chat_history_guest_{session_id}"
    history = cache.get(key, [])
    return history[-limit:]


# def save_chat_turn(user, session_id, role=None, message=None, name=None, full_message=None):
#     """
#     Saves a chat turn to cache. 
#     - If `full_message` is provided, stores it directly (must be a dict with keys like role, content, etc).
#     - Otherwise builds message from role + content (+ name if role is 'function').
#     """
#     key = f"chat_history_user_{user.id}" if user and user.is_authenticated else f"chat_history_guest_{session_id}"
#     history = cache.get(key, [])

#     if full_message:
#         history.append(full_message)
#     else:
#         data = {"role": role, "content": message}
#         if role == "function":
#             if not name:
#                 raise ValueError("Function role requires a name field.")
#             data["name"] = name
#         history.append(data)

#     cache.set(key, history, timeout=600)

def save_chat_turn(user, session_id, role=None, message=None, full_message=None, name=None):
    key = f"chat_history_user_{user.id}" if user and user.is_authenticated else f"chat_history_guest_{session_id}"
    history = cache.get(key, [])
    if full_message:
        history.append(full_message)
    else:
        msg = {"role": role, "content": message}
        if name:
            msg["name"] = name
        history.append(msg)
    cache.set(key, history, timeout=600)

def save_to_db_conversation(user, session_id, role=None, message=None, full_message=None):
    if full_message:
        role = full_message.get("role")
        if role == "function":
            name = full_message.get("name", "unknown_function")
            content = full_message.get("content", "")
            message = f"[{name}] {content}"
        else:
            message = full_message.get("content", "")
    else:
        message = message or ""

    if message and len(message) > 500:
        message = message[:497] + "..."

    ChatHistory.objects.create(
        user=user if user and user.is_authenticated else None,
        session_id=session_id,
        role=role,
        message=message
    )

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
        return "Bhaiya" if age is None or age < 40 else "Chacha"
    elif gender == "F":
        if age is None:
            return "Didi"
        if age < 40:
            return "Bahini"
        elif age < 50:
            return "didi"
        else:
            return "Mataji"
    return "Mitra"

# -------------------------------
# User profile context
def get_user_context(user):
    if not user.is_authenticated:
        return "No user is logged in, so help in general terms and manner."

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
Ka ho {user.username} {address_as.upper()}, sab theek ba?

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


def friendly_date_string(date_obj):
    """
    Given a date object, returns a string like '19th July, 2025'.
    """
    day = date_obj.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix} {date_obj.strftime('%B, %Y')}"