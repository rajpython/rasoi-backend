import json
from datetime import datetime
from django.utils import timezone
from restaurante.models import Booking, TIME_SLOTS
from restaurante.serializers import BookingSerializer
from restaurante.views import BookingViewSet
from dateutil import parser  # requires `pip install python-dateutil`
from restaurante.utils import format_slot, friendly_date_string

# def parse_date_string(date_str):
#     """
#     Parses a string like 'July 15' or '2025-07-15' into a date object.
#     """
#     try:
#         return parser.parse(date_str).date()
#     except Exception:
#         raise ValueError("Could not understand the date. Please provide a valid date like '2025-07-15'.")
    

# def parse_date_string(date_str):
#     """
#     Parses a string like 'July 15' or '22nd July' and ensures it's in the future.
#     If no year is specified or it parses to the past, bumps to next appropriate year.
#     """
#     today = datetime.today()
#     try:
#         date = parser.parse(date_str, fuzzy=True, default=today)
#         if date.date() < today.date():
#             # If parsed date ended up before today, assume it's for next year
#             date = date.replace(year=today.year + 1)
#         return date.date()
#     except Exception:
#         raise ValueError("Could not understand the date. Please provide something like 'July 25' or 'next Friday'.")

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



def get_available_booking_times(reservation_date):
    """
    Given a date string, returns available time slots.
    """
    # Parse natural language to date string
    date_obj = parse_date_string(reservation_date)
    booked = Booking.objects.filter(
        reservation_date=date_obj
    ).values_list("reservation_time", flat=True)

    available = [slot for slot, _ in TIME_SLOTS if slot not in booked]
    # New: format slots before returning
    formatted_slots = [format_slot(slot) for slot in available]
    return f"The available slots for {friendly_date_string(date_obj)} are: " \
    + ", ".join(formatted_slots) + "." +"Please pick up one."

# def validate_booking_time(chosen_time, available_slots):
#     is_valid = chosen_time in available_slots
#     return {"valid": is_valid}

def validate_booking_time(chosen_time, available_slots):
    """
    Checks if chosen time is available, returns conversational response.
    """
    is_valid = chosen_time in available_slots
    if is_valid:
        return {
            "valid": True,
            "message": f"Are wah! {chosen_time} slot available hai 🎉. Confirm?"
        }
    else:
        return {
            "valid": False,
            "message": f"Arey sorry yaar 😅, {chosen_time} time available nahi hai. Koi aur time try karo?"
        }

def create_booking(
    reservation_date, reservation_time, no_of_guests, occasion, email=None, user=None
):
    """
    Creates a booking and sends confirmation email.
    Fills email from user if missing.
    """
    # Parse the date
    date_obj = parse_date_string(reservation_date)

    # Fallback to user email
    if (not email or email == "") and user and user.is_authenticated:
        email = user.email

    if not email:
        return "I need an email address to confirm your booking. Please provide it."

    # Actually create booking
    booking = Booking.objects.create(
        user=user if user and user.is_authenticated else None,
        reservation_date=date_obj,
        reservation_time=reservation_time,
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

# ✅ TOOL FUNCTION MAP
TOOL_FUNCTION_MAP = {
    "get_available_booking_times": get_available_booking_times,
    "validate_booking_time": validate_booking_time,
    "create_booking": create_booking,
}

