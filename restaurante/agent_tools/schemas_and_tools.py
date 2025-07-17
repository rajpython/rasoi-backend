
from pydantic import BaseModel
from typing import Optional

# ------------------------
# ORDERING SCHEMAS
# ------------------------

class StartOrderSchema(BaseModel):
    pass

class AddOrderItemSchema(BaseModel):
    order_id: int
    menuitem_id: int
    quantity: int

class CheckoutOrderSchema(BaseModel):
    order_id: int
    delivery_type: str  # "pickup" or "delivery"
    delivery_time_slot: str
    payment_method: str  # "stripe" or "cod"
    delivery_address: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_pin: Optional[str] = None

class AvailableSlotsTodaySchema(BaseModel):
    pass

class CreatePaymentIntentSchema(BaseModel):
    order_id: int

# ------------------------
# AGENTIC TOOLS REGISTRY
# ------------------------

AGENTIC_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "start_order",
            "description": "Starts a new order for the logged-in user.",
            "parameters": StartOrderSchema.schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_order_item",
            "description": "Adds an item to the ongoing order.",
            "parameters": AddOrderItemSchema.schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "checkout_order",
            "description": "Finalizes delivery, time, payment details.",
            "parameters": CheckoutOrderSchema.schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "available_delivery_slots_today",
            "description": "Lists available delivery or pickup slots today.",
            "parameters": AvailableSlotsTodaySchema.schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_payment_intent",
            "description": "Returns payment URL for frontend Stripe checkout.",
            "parameters": CreatePaymentIntentSchema.schema()
        }
    }
]
