# restaurante/stripe_payment.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import stripe
from decimal import Decimal

from .models import Cart

stripe.api_key = settings.STRIPE_SECRET_KEY

class CreatePaymentIntent(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        cart_items = Cart.objects.filter(user=user)
        if not cart_items.exists():
            return Response({"error": "No items in cart"}, status=400)
        
        # Calculate total in cents
        total_amount = sum(item.price for item in cart_items)
        amount_cents = int(total_amount * Decimal(1.2))  # e.g. rs. 100->120c

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                automatic_payment_methods={"enabled": True},
                metadata={"user_id": user.id}
            )
            return Response({
                "client_secret": intent.client_secret
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)
