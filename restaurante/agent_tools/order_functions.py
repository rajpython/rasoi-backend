from restaurante.models import Order, OrderItem, MenuItem
from restaurante.models import DELIVERY_TIME_SLOTS
from django.utils import timezone

def start_order(user):
    order = Order.objects.create(user=user)
    return {"order_id": order.id, "message": f"✅ Naya order start ho gaya! (ID: {order.id})"}


def add_order_item(order_id, menuitem_id, quantity):
    order = Order.objects.get(id=order_id)
    item = MenuItem.objects.get(id=menuitem_id)

    unit_price = item.price
    total_price = unit_price * quantity

    OrderItem.objects.create(
        order=order,
        menuitem=item,
        quantity=quantity,
        price=total_price  # item.price * quantity
    )

    return {
        "message": f"🛒 {quantity} x {item.title} (@ ₹{unit_price}) added to order #{order_id}!"
    }


def available_delivery_slots_today():
    now = timezone.localtime()
    upcoming_slots = ["ASAP"]
    for slot, _ in DELIVERY_TIME_SLOTS:
        if slot != "ASAP":
            h, m = map(int, slot.split(":"))
            slot_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if slot_time > now:
                upcoming_slots.append(slot)
    return {"available_slots": upcoming_slots}

def checkout_order(order_id, delivery_type, delivery_time_slot, payment_method,
                   delivery_address=None, delivery_city=None, delivery_pin=None):
    order = Order.objects.get(id=order_id)
    order_items = OrderItem.objects.filter(order=order)
    total = sum(item.price for item in order_items)
    order.total = total
    order.delivery_type = delivery_type
    order.delivery_time_slot = delivery_time_slot
    order.payment_method = payment_method
    if delivery_type == "delivery":
        order.delivery_address = delivery_address
        order.delivery_city = delivery_city
        order.delivery_pin = delivery_pin
    order.save()
    return {
        "message": f"✅ Order #{order.id} finalized! Total: ₹{total}. Slot: {delivery_time_slot}, Payment: {payment_method}"
    }

def create_payment_intent(order_id):
    order = Order.objects.get(id=order_id)
    if not order.total:
        order_items = OrderItem.objects.filter(order=order)
        order.total = sum(item.price for item in order_items)
        order.save()

    return {
        "message": f"💳 To pay ₹{order.total}, please complete your order at:\n"
                   f"👉 https://localhost:3000/cart?order_id={order.id}"
    }
