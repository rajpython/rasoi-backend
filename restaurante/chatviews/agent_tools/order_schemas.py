
from pydantic import BaseModel
from typing import Optional

# ------------------------
# ORDERING SCHEMAS
# ------------------------

class StartOrderSchema(BaseModel):
    pass

class AddOrderItemSchema(BaseModel):
    order_id: int
    menuitem_title: str
    quantity: int

class ReviseOrderItemSchema(BaseModel):
    order_id: int
    menuitem_title: str
    quantity: int  # 0 to delete


class CheckoutOrderSchema(BaseModel):
    order_id: int
    delivery_type: str  # "pickup" or "delivery"
    delivery_date: str  # ✅ Newly added
    delivery_time_slot: str
    payment_method: str  # "stripe" or "cod"
    delivery_address: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_pin: Optional[str] = None

class DeleteOrderSchema(BaseModel):
    order_id: int


class SetDeliveryDateSchema(BaseModel):
    order_id: int
    delivery_date: str  # e.g. "2025-08-10" or keywords already normalized upstream

class SetDeliveryTimeSlotSchema(BaseModel):
    order_id: int
    delivery_time_slot: str  # e.g. "ASAP" or "18:30"

class SetDeliveryTypeSchema(BaseModel):
    order_id: int
    delivery_type: str  # "delivery" or "pickup"

class SetDeliveryDetailsSchema(BaseModel):
    order_id: int
    delivery_address: str
    delivery_city: str
    delivery_pin: str

class SetPaymentMethodSchema(BaseModel):
    order_id: int
    payment_method: str  # "stripe" or "cod"



# class CheckoutOrderSchema(BaseModel):
#     order_context: dict  # send entire context collected from prior steps


class AvailableSlotsTodaySchema(BaseModel):
    pass

# class CreatePaymentIntentSchema(BaseModel):
#     order_id: int


# class GetOrderContextSchema(BaseModel):
#     order_id: int


# ------------------------
# AGENTIC TOOLS REGISTRY
# ------------------------

ORDER_AGENTIC_TOOLS = [
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
            "name": "revise_order_item",
            "description": "Changes quantity of an item in the order, or deletes it if quantity is 0.",
            "parameters": ReviseOrderItemSchema.schema()
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
        "name": "delete_order",
        "description": "Deletes the current order and clears the context. Use this if the user wants to cancel the order entirely.",
        "parameters": DeleteOrderSchema.schema(),
    }
},
{
        "type": "function",
        "function": {
            "name": "set_delivery_date",
            "description": "Persist the chosen delivery date for the current order.",
            "parameters": SetDeliveryDateSchema.schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_delivery_time_slot",
            "description": "Persist the chosen delivery/pickup time slot for the current order.",
            "parameters": SetDeliveryTimeSlotSchema.schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_delivery_type",
            "description": "Persist delivery or pickup choice for the current order.",
            "parameters": SetDeliveryTypeSchema.schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_delivery_details",
            "description": "Persist delivery address details (address, city, pin).",
            "parameters": SetDeliveryDetailsSchema.schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_payment_method",
            "description": "Persist payment method for the current order.",
            "parameters": SetPaymentMethodSchema.schema()
        }
    }
]
