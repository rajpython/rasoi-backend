import json
from datetime import datetime
from django.utils import timezone
from restaurante.models import Booking, TIME_SLOTS
from restaurante.serializers import BookingSerializer
from restaurante.views import BookingViewSet
from dateutil import parser  # requires `pip install python-dateutil`
from restaurante.utils import format_slot, friendly_date_string
from django.core.cache import cache

def parse_date_string(date_str):
    today = datetime.today()
    try:
        # Parse the string into a datetime, but default to THIS year first
        date = parser.parse(date_str, fuzzy=True, default=datetime(today.year, 1, 1))

        # If year is LESS than today, or same year but month/day is before today, bump to next year
        if (date.year < today.year) or (date.year == today.year and date.month < today.month) or \
           (date.year == today.year and date.month == today.month and date.day < today.day):
            date = date.replace(year=today.year + 1)

        return date.date()
    except Exception:
        raise ValueError("Could not understand the date. Please provide something like 'July 25' or 'next Friday'.")



def get_available_booking_times(selected_date):
    """
    Given a date string, returns available time slots.
    """
    # Parse natural language to date string
    date_obj = parse_date_string(selected_date)
    booked = Booking.objects.filter(
        reservation_date=date_obj
    ).values_list("reservation_time", flat=True)

    available = [slot for slot, _ in TIME_SLOTS if slot not in booked]
    # New: format slots before returning
    formatted_slots = [format_slot(slot) for slot in available]
    # return f"The available slots for {friendly_date_string(date_obj)} are: " \
    # + ", ".join(formatted_slots) + "." +"Please pick up one."
    return {
        "available_slots": available,  # raw slot strings like '17:30'
        "message": f"The available slots for {friendly_date_string(date_obj)} are: " +
                   ", ".join(formatted_slots) + ". Please pick one."
    }

def validate_booking_time(selected_time, available_slots):
    """
    Checks if chosen time is available, returns conversational response.
    """
    is_valid = selected_time in available_slots
    if is_valid:
        return {
            "valid": True,
            "message": f"Are wah! {selected_time} slot available hai 🎉. Confirm?"
        }
    else:
        return {
            "valid": False,
            "message": f"Arey sorry yaar 😅, {selected_time} time available nahi hai. Koi aur time try karo?"
        }

def create_booking(
    selected_date, selected_time, no_of_guests, occasion, email=None, user=None
):
    """
    Creates a booking and sends confirmation email.
    Fills email from user if missing.
    """
    # Parse the date
    date_obj = parse_date_string(selected_date)

    # Fallback to user email
    if (not email or email == "") and user and user.is_authenticated:
        email = user.email

    if not email:
        return "I need an email address to confirm your booking. Please provide it."

    # Actually create booking
    booking = Booking.objects.create(
        user=user if user and user.is_authenticated else None,
        reservation_date=date_obj,
        reservation_time= selected_time,
        no_of_guests=no_of_guests,
        occasion=occasion,
        email=email
    )

    # Use your existing email formatting exactly
    BookingViewSet().send_confirmation_email(booking)

    # Return a nicely formatted confirmation summary
    return f"""
✅ Booking confirmed for {booking.reservation_date.strftime('%B %d, %Y')} at {booking.reservation_time}.
Guests: {booking.no_of_guests}, Occasion: {booking.occasion}
Reference: {booking.reference_number}
A confirmation email has been sent to {booking.email}.
"""
def cancel_booking(cancel: bool, session_id: str) -> dict:
    if not cancel:
        return {"message": "👍 No problem. Let us continue on booking a table!"}

    booking_key = f"booking_context_{session_id}"
    cache.delete(booking_key)
    cache.delete(f"chat_mode_{session_id}")
    return {
        "message": "🚫 Booking process cancelled. Let me know if you'd like to start again!"
    }


# ✅ TOOL FUNCTION MAP
TOOL_FUNCTION_MAP = {
    "get_available_booking_times": get_available_booking_times,
    "validate_booking_time": validate_booking_time,
    "create_booking": create_booking,
    "cancel_booking": cancel_booking,
}

# ===== Tool function implementations (simple; booking_logic persists) =====

# def set_no_of_guests(no_of_guests: int):
#     return {"no_of_guests": no_of_guests}

# def _normalize_occasion(occasion: str) -> str:
#     o = (occasion or "").strip().lower()
#     if o in {"birthday", "bday"}:
#         return "Birthday"
#     if o in {"anniversary", "anniv"}:
#         return "Anniversary"
#     if o in {"other", "none", "na"}:
#         return "Other"
#     # short free-text fallback
#     return occasion.strip()[:64] or "Other"

# def set_occasion(occasion: str):
#     return {"occasion": _normalize_occasion(occasion)}

# def set_email(email: str):
#     # pydantic EmailStr in schema already validates; just echo back
#     return {"email": email}


def set_no_of_guests(no_of_guests: int):
    """
    Persist guest count and guide the user to the next step via `message`.
    """
    try:
        n = int(no_of_guests)
    except (TypeError, ValueError):
        return {
            "message": "Guests ka number samajh nahi aaya. Kripya ek poora number batayein (e.g., 2, 4, 6)."
        }

    if n <= 0:
        return {
            "message": "Guests kam se kam 1 hona chahiye. Kripya sahi number batayein."
        }

    return {
        "no_of_guests": n,
        "message": f"Noted — {n} guests. Okay?"
    }


def _normalize_occasion(occasion: str) -> str:
    o = (occasion or "").strip().lower()
    if o in {"birthday", "bday"}:
        return "Birthday"
    if o in {"anniversary", "anniv"}:
        return "Anniversary"
    if o in {"other", "none", "na"}:
        return "Other"
    # short free-text fallback (kept minimal)
    return (occasion or "Other").strip()[:64] or "Other"


def set_occasion(occasion: str):
    """
    Persist occasion and guide to email step using a neutral prompt that works
    whether the user has a saved email or wants to provide one.
    """
    normalized = _normalize_occasion(occasion)
    return {
        "occasion": normalized,
        "message": f"Occasion set: {normalized}. Okay?"
    }


# def set_email(email: str):
#     """
#     Persist email and nudge towards final confirmation. (Create-booking summary
#     will be produced by the model from context; we keep this message short.)
#     """
#     # Schema already validates EmailStr; this is just a friendly fallback.
#     if not email or "@" not in email:
#         return {
#             "message": "Yeh email sahi nahi lag raha. Kripya ek valid email dijiye (e.g., name@example.com)."
#         }

#     return {
#         "email": email.strip(),
#         "message": "Email save ho gaya. Okay?"
#     }

def set_email(email: str):
    """
    Persist email and nudge towards final confirmation. (Create-booking summary
    will be produced by the model from context; we keep this message short.)
    """
    email_clean = (email or "").strip()
    if "@" not in email_clean:
        return {"message": "Yeh email sahi nahi lag raha. Kripya ek valid email dijiye (e.g., name@example.com)."}

    return {
        "email": email_clean,
        # use concatenation to avoid any f/format confusion or later .format() passes
        "message": "Email " + email_clean + " set ho gaya. Okay?"
    }



# ✅ Add to TOOL_FUNCTION_MAP
TOOL_FUNCTION_MAP.update({
    "set_no_of_guests": set_no_of_guests,
    "set_occasion": set_occasion,
    "set_email": set_email,
})
