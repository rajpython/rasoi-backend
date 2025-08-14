
from pydantic import BaseModel, EmailStr
from typing import Optional, List

# For use by OpenAI tool schemas
class GetAvailableBookingTimesSchema(BaseModel):
    selected_date: str

class ValidateBookingTimeSchema(BaseModel):
    selected_time: str
    available_slots: List[str]

class CreateBookingSchema(BaseModel):
    selected_date: str
    selected_time: str
    no_of_guests: int
    occasion: str
    email: str

class SetGuestsSchema(BaseModel):
    no_of_guests: int  # >=1 (you can enforce min in pydantic if you like)

class SetOccasionSchema(BaseModel):
    occasion: str  # e.g. "Birthday", "Anniversary", "Other", or free text

class SetEmailSchema(BaseModel):
    email: EmailStr  # basic validation



class CancelBookingSchema(BaseModel):
    cancel: bool  # GPT must say true only if user has clearly said to cancel


AGENTIC_TOOLS = [
        {
        "type": "function",
        "function": {
            "name": "validate_booking_time",
            "description": "Check if the chosen time is in the available slots. Returns valid: true/false.",
            "parameters": ValidateBookingTimeSchema.schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_booking_times",
            "description": "Get available booking time slots for a given reservation date.",
            "parameters": GetAvailableBookingTimesSchema.schema()
        }
    },
    # ✅ NEW setters the model can call as soon as the user provides values
    {
        "type": "function",
        "function": {
            "name": "set_no_of_guests",
            "description": "Set or update the number of guests for the current booking.",
            "parameters": SetGuestsSchema.schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_occasion",
            "description": "Set or update the occasion (Birthday, Anniversary, Other, or short description).",
            "parameters": SetOccasionSchema.schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_email",
            "description": "Set or update the email to use for booking confirmation.",
            "parameters": SetEmailSchema.schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_booking",
            "description": "Book a table for the user with all necessary details.",
            "parameters": CreateBookingSchema.schema()
        }
    },
        {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Cancels the current booking process and clears booking context cache.",
            "parameters": CancelBookingSchema.schema()
        }
    }
]