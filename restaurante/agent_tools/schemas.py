# AGENTIC_TOOLS = [
#     {
#         "type": "function",
#         "function": {
#             "name": "get_available_booking_times",
#             "description": (
#                 "Get available time slots for a given reservation date. "
#                 "Date can be '2025-07-15' or natural language like 'July 15'."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "reservation_date": {
#                         "type": "string",
#                         "description": "Reservation date. User can say 'July 15' or 'next Friday'."
#                     },
#                 },
#                 "required": ["reservation_date"],
#             }
#         }
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "create_booking",
#             "description": (
#                 "Book a table. Will fallback on logged-in user's email if not provided."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "reservation_date": {"type": "string", "description": "Date in YYYY-MM-DD or natural format"},
#                     "reservation_time": {"type": "string", "description": "Time slot e.g. '18:30'"},
#                     "no_of_guests": {"type": "integer"},
#                     "occasion": {"type": "string"},
#                     "email": {"type": "string", "description": "Customer email (optional if logged in)"}
#                 },
#                 "required": ["reservation_date", "reservation_time", "no_of_guests", "occasion"]
#             }
#         }
#     }
# ]


#     {
#         "type": "function",
#         "function": {
#             "name": "get_menu_categories",
#             "description": "List all menu categories.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {}
#             }
#         }
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "get_menu_items",
#             "description": "List menu items in a category.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "category": {"type": "string"}
#                 },
#                 "required": ["category"]
#             }
#         }
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "create_order",
#             "description": "Start a new order for the current user.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {}
#             }
#         }
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "add_order_item",
#             "description": "Add an item to an order.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "order_id": {"type": "integer"},
#                     "menuitem_id": {"type": "integer"},
#                     "quantity": {"type": "integer"},
#                 },
#                 "required": ["order_id", "menuitem_id", "quantity"]
#             }
#         }
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "checkout_order",
#             "description": "Checkout the order: choose delivery/pickup, delivery details, and payment method.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "order_id": {"type": "integer"},
#                     "delivery_type": {"type": "string", "enum": ["pickup", "delivery"]},
#                     "delivery_address": {"type": "string"},
#                     "delivery_city": {"type": "string"},
#                     "delivery_pin": {"type": "string"},
#                     "delivery_time_slot": {"type": "string"},
#                     "payment_method": {"type": "string", "enum": ["stripe", "cod"]},
#                 },
#                 "required": ["order_id", "delivery_type", "payment_method"]
#             }
#         }
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "create_payment_intent",
#             "description": "Generate a Stripe payment link for the order.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "order_id": {"type": "integer"},
#                 },
#                 "required": ["order_id"]
#             }
#         }
#     }
# ]


from pydantic import BaseModel
from typing import Optional, List

# For use by OpenAI tool schemas
class GetAvailableBookingTimesSchema(BaseModel):
    reservation_date: str

class ValidateBookingTimeSchema(BaseModel):
    chosen_time: str
    available_slots: List[str]

class CreateBookingSchema(BaseModel):
    reservation_date: str
    reservation_time: str
    no_of_guests: int
    occasion: str
    email: str

class CreateOrderSchema(BaseModel):
    items: List[int]
    delivery_time: str
    delivery_type: str
    payment_method: str


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
            "name": "create_order",
            "description": "Create a food order with selected items, delivery and payment info.",
            "parameters": CreateOrderSchema.schema()
        }
    }
]