from django.core.management.base import BaseCommand
from django.utils.timezone import now, make_aware
from restaurante.models import Order
from datetime import datetime, time

class Command(BaseCommand):
    help = "Deletes unconfirmed orders where delivery time is in the past"

    def handle(self, *args, **options):
        current_time = now()
        today = current_time.date()
        deleted_count = 0

        # Get all unconfirmed orders
        unconfirmed_orders = Order.objects.filter(is_confirmed=False)

        for order in unconfirmed_orders:
            try:
                delivery_date = order.date
                delivery_slot = order.delivery_time_slot

                # Case 1: delivery date is in the past (delete regardless of time slot)
                if delivery_date < today:
                    order.delete()
                    deleted_count += 1
                    continue

                # Case 2: delivery date is today
                if delivery_date == today:
                    if delivery_slot == "ASAP":
                        continue  # treat as still valid

                    # Parse HH:MM time
                    h, m = map(int, delivery_slot.split(":"))
                    delivery_dt = datetime.combine(delivery_date, time(h, m))
                    delivery_dt = make_aware(delivery_dt)

                    if delivery_dt < current_time:
                        order.delete()
                        deleted_count += 1

            except Exception as e:
                self.stderr.write(self.style.WARNING(
                    f"⚠️ Skipped order #{order.id} due to error: {str(e)}"
                ))

        if deleted_count > 0:
            self.stdout.write(self.style.SUCCESS(
                f"✅ Deleted {deleted_count} unconfirmed order(s) with past delivery times."
            ))
        else:
            self.stdout.write("ℹ️ No unconfirmed orders to delete.")
