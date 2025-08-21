import json
from datetime import datetime
from django.utils import timezone
from restaurante.models import Booking, TIME_SLOTS
from restaurante.serializers import BookingSerializer
from restaurante.views import BookingViewSet
from dateutil import parser  # requires `pip install python-dateutil`
from restaurante.utils import format_slot, friendly_date_string
from django.core.cache import cache
import pytz

IST = pytz.timezone("Asia/Kolkata")


def parse_date_string(date_str):
    ist_now = datetime.now(IST)
    try:
        # Use IST-based default for parsing fuzzy strings
        default_dt = datetime(ist_now.year, 1, 1, tzinfo=IST)
        date = parser.parse(date_str, fuzzy=True, default=default_dt)

        # Ensure parsed date is in IST
        date = date.astimezone(IST)

        # Year rollover logic
        if (date.year < ist_now.year) or \
           (date.year == ist_now.year and date.month < ist_now.month) or \
           (date.year == ist_now.year and date.month == ist_now.month and date.day < ist_now.day):
            date = date.replace(year=ist_now.year + 1)

        return date.date()
    except Exception:
        raise ValueError("Could not understand the date. Please provide something like 'July 25' or 'next Friday'.")


def get_available_booking_times(selected_date):
    """
    Given a date string, returns available time slots.
    """
    # Parse natural language to date string
    date_obj = parse_date_string(selected_date)
    # date_obj = selected_date
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
            "message": f"{selected_time} is available 🎉. Confirm?"
        }
    else:
        return {
            "valid": False,
            "message": f"Shoot 😅, {selected_time} time not available. Try another please?"
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
    # date_obj = selected_date

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


def set_no_of_guests(no_of_guests: int):
    """
    Persist guest count and guide the user to the next step via `message`.
    """
    try:
        n = int(no_of_guests)
    except (TypeError, ValueError):
        return {
            "message": "Didn't understand. Please choose integers (e.g., 2, 4, 6)."
        }

    if n <= 0:
        return {
            "message": "At least one guest needed, we can't let you steal our guests!"
        }

    return {
        "no_of_guests": n,
        "message": f"Alright, {n} guests. Proceed further?"
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
        "message": f"{normalized} it is! Move on?"
    }



def set_email(email: str):
    """
    Persist email and nudge towards final confirmation. (Create-booking summary
    will be produced by the model from context; we keep this message short.)
    """
    email_clean = (email or "").strip()
    if "@" not in email_clean:
        return {"message": "Please provide a valid email(e.g., name@example.com)."}

    return {
        "email": email_clean,
        # use concatenation to avoid any f/format confusion or later .format() passes
        "message": "Email " + email_clean + " set. All good?"
    }



# ✅ Add to TOOL_FUNCTION_MAP
TOOL_FUNCTION_MAP.update({
    "set_no_of_guests": set_no_of_guests,
    "set_occasion": set_occasion,
    "set_email": set_email,
})
