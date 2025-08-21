from restaurante.models import Order, OrderItem, MenuItem
from restaurante.models import DELIVERY_TIME_SLOTS
# from django.utils import timezone
from restaurante.utils import clear_order_context
from django.core.cache import cache

from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

def available_delivery_slots(delivery_date: str) -> dict:
    """
    Returns available delivery slots for the given date.
    - For today: filters out past slots.
    - For future: returns all slots.
    """
    today_str = datetime.now(IST).date().isoformat()
    
    if delivery_date == today_str:
        now = datetime.now(IST)
        upcoming_slots = ["ASAP"]
        for slot, _ in DELIVERY_TIME_SLOTS:
            if slot != "ASAP":
                h, m = map(int, slot.split(":"))
                slot_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if slot_time > now:
                    upcoming_slots.append(slot)
                   
        return {"delivery_date": delivery_date,
            "available_slots": upcoming_slots}
    else:
        # All slots valid for future dates
        return {"delivery_date": delivery_date,
            "available_slots": [slot for slot, _ in DELIVERY_TIME_SLOTS]}



def start_order(user):
    order = Order.objects.create(user=user)
    return {
        "order_id": order.id,
        "message": f"✅ Your order has started! (Order ID: {order.id}) Let's start with your first item to add. 🍽️ \
        Let me know if you want to browse menu or categories"
    }



def add_order_item(order_id, menuitem_title, quantity):
    order = Order.objects.get(id=order_id)
    item = MenuItem.objects.get(title=menuitem_title)
    unit_price = item.price

    # 👇 Prevent UNIQUE constraint errors
    order_item, created = OrderItem.objects.get_or_create(
        order=order,
        menuitem=item,
        defaults={"quantity": 0, "price": 0}
    )
    if created:
        order_item.quantity = quantity
    else:
        # additive semantics: add to existing qty
        order_item.quantity += quantity

    order_item.price = unit_price * order_item.quantity
    order_item.save()

    order_items = OrderItem.objects.filter(order=order)
    item_list = [
        {"title": i.menuitem.title, "qty": i.quantity, "price": float(i.price)}
        for i in order_items
    ]

    return {
        "message": (
            f"🛒 Added {quantity} x {item.title} (@ ₹{unit_price:.2f}) to Order #{order_id} "
            f"(now {order_item.quantity} total)."
        ),
        "items": item_list
    }



def revise_order_item(order_id, menuitem_title, quantity):
    order = Order.objects.get(id=order_id)
    try:
        item = MenuItem.objects.get(title=menuitem_title)
    except MenuItem.DoesNotExist:
        return {"message": f"❌ Item '{menuitem_title}' not found in our menu."}

    try:
        order_item = OrderItem.objects.get(order=order, menuitem=item)
    except OrderItem.DoesNotExist:
        return {"message": f"❌ '{menuitem_title}' not found in your order."}

    if quantity == 0:
        order_item.delete()
        msg = f"🗑️ '{menuitem_title}' has been removed from your order."
    else:
        order_item.quantity = quantity
        order_item.price = item.price * quantity
        order_item.save()
        msg = f"✏️ '{menuitem_title}' quantity updated to {quantity}."

    updated_items = OrderItem.objects.filter(order=order)
    item_list = [
        {"title": i.menuitem.title, "qty": i.quantity, "price": float(i.price)}
        for i in updated_items
    ]

    return {
        "message": msg,
        "items": item_list
    }


def checkout_order(user, order_id, delivery_type, delivery_date, delivery_time, payment_method,
                   delivery_address=None, delivery_city=None, delivery_pin=None):
    order = Order.objects.get(id=order_id)

    if order.is_confirmed:
        return {
            "message": f"⚠️ Order #{order_id} has already been confirmed and cannot be checked out again."
        }
    
    order_items = OrderItem.objects.filter(order=order)
    total = sum(item.price for item in order_items)
    order.total = total
    order.delivery_type = delivery_type
    order.date = delivery_date
    order.delivery_time_slot = delivery_time
    order.payment_method = payment_method

    print("🛂 checkout_order received:", {
    "delivery_type": delivery_type,
    "address": delivery_address,
    "city": delivery_city,
    "pin": delivery_pin,
    "date": delivery_date,
    "payment_method": payment_method
})
    if delivery_type and delivery_type.lower() == "delivery":
        order.delivery_address = delivery_address
        order.delivery_city = delivery_city
        order.delivery_pin = delivery_pin
    order.save()
   
    context = get_order_context(order_id)
    if not isinstance(context, dict):
        print(f"⚠️ Unexpected context type: {type(context)} — returning fallback.")
        return {
            "message": "✅ Finalized",
            "note": str(context)
        }

    return {
        "message": "✅ Finalized",
        **context
    }


def get_order_context(order_id):
    order = Order.objects.get(id=order_id)
    items = OrderItem.objects.filter(order=order)

    context = {
        "order_id": order.id,
        "items": [
            {
                "menuitem": item.menuitem.title,
                "quantity": item.quantity,
                "unit_price": str(item.menuitem.price),
                "subtotal": str(item.price)
            } for item in items
        ],
        "delivery_type": order.delivery_type or "not yet",
        "delivery_date": order.date.isoformat() if order.date else "not yet",
        "delivery_time": order.delivery_time_slot or "not yet",
        "payment_method": order.payment_method or "not yet",
        "total": str(sum(item.price for item in items)),
        "is_confirmed": order.is_confirmed  # ✅ Include this
    }

    # Add delivery address info explicitly if delivery_type is "delivery"
    if order.delivery_type and order.delivery_type.lower() == "delivery":
        context.update({
            "delivery_address": order.delivery_address or "not applicable",
            "delivery_city": order.delivery_city or "not applicable",
            "delivery_pin": order.delivery_pin or "not applicable"
        })
    else:
        context.update({
            "delivery_address": "not applicable",
            "delivery_city": "not applicable",
            "delivery_pin": "not applicable"
        })

    print("📦 get_order_context delivery info:", {
        "delivery_address": order.delivery_address,
        "delivery_city": order.delivery_city,
        "delivery_pin": order.delivery_pin,
        "delivery_type": order.delivery_type
    })


    return context

    
def delete_order(order_id: int, session_id: str):
    try:
        print(f"🧹 Deleting order {order_id} for session_id={session_id}")
        order = Order.objects.get(id=order_id)

        if order.is_confirmed:
            return {"message": "⚠️ Confirmed orders cannot be deleted."}

        order.delete()

        clear_order_context(session_id)
        cache.delete(f"chat_mode_{session_id}")
        print(f"✅ Deleted chat_mode_{session_id}")

        return {"message": f"🗑️ Order #{order_id} deleted successfully."}
    
    except Order.DoesNotExist:
        return {"message": "❌ Order not found or already deleted."}

    
# SOME ADDITIONAL FUNCTIONS

def _get_order(order_id: int) -> Order:
    return Order.objects.get(id=order_id)


# --- CACHE-ONLY SETTERS (no DB writes) ---

def set_delivery_date(delivery_date: str):
    # normalize is already done upstream
    return {
        "delivery_date": delivery_date,
        "message": f"📅 Delivery date set to {delivery_date}."
    }

def set_delivery_time_slot(delivery_time_slot: str):
    return {
        "delivery_time_slot": delivery_time_slot,
        "message": f"⏰ Time slot set to {delivery_time_slot}."
    }

def set_delivery_type(delivery_type: str):
    return {
        "delivery_type": delivery_type,
        "message": f"🚚 Method set to {delivery_type}."
    }

def set_delivery_details( delivery_address: str, delivery_city: str, delivery_pin: str):
    return {
        "delivery_address": delivery_address,
        "delivery_city": delivery_city,
        "delivery_pin": delivery_pin,
        "message": "📍 Delivery address saved."
    }

def set_payment_method(payment_method: str):
    return {
        "payment_method": payment_method,
        "message": f"💳 Payment method set to {payment_method}."
    }

ORDER_TOOL_FUNCTION_MAP = {
    "start_order": start_order,
    "add_order_item": add_order_item,
    "revise_order_item": revise_order_item,
    "checkout_order": checkout_order,
    "available_delivery_slots": available_delivery_slots,
    "delete_order": delete_order,
    # "set_delivery_date": set_delivery_date,
    # "set_delivery_time_slot": set_delivery_time_slot,
    "set_delivery_type": set_delivery_type,
    "set_delivery_details": set_delivery_details,
    "set_payment_method": set_payment_method,
}

def validate_delivery_time(delivery_time: str, available_slots: list) -> dict:
    """
    Validates if the user-selected delivery time is in the list of available slots.
    """
    if delivery_time in available_slots:
        return {
            "valid": True,
            "message": f"{delivery_time} it is!"
        }
    else:
        return {
            "valid": False,
            "message": f"Oops! {delivery_time} not. Please choose another time."
        }


ORDER_TOOL_FUNCTION_MAP.update({
    "validate_delivery_time": validate_delivery_time,
})
