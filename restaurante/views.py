from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import Group, User


from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework import generics, viewsets, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt



from .models import Category, MenuItem, Cart, Order, OrderItem, Booking, TIME_SLOTS, DELIVERY_TIME_SLOTS
from .serializers import BookingSerializer, CategorySerializer, MenuItemSerializer, \
    CartSerializer, OrderSerializer, UserSerializer, UserRegistrationSerializer, UserWithProfileSerializer
from .permissions import IsManager, IsDeliveryCrew, IsManagerOrAdminForSafe

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from django.conf import settings

from .models import CustomerReview
from .serializers import CustomerReviewSerializer



# Create your views here.

def index(request):
    return render(request, 'index.html', {})


# @method_decorator(csrf_exempt, name='dispatch')
class BookingViewSet(viewsets.ModelViewSet):
    # queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    # permission_classes = [AllowAny]
    
    def get_permissions(self):
        if getattr(self, "action", None) == "manage_by_reference":
            return [AllowAny()]
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            # For normal users, show only their reservations
            if user.is_staff or user.is_superuser or user.groups.filter(name="manager").exists():
                return Booking.objects.all().order_by('-reservation_date', '-reservation_time')
            return Booking.objects.filter(user=user).order_by('-reservation_date', '-reservation_time')
        # For non-logged-in users, return nothing (or could allow showing NONE)
        return Booking.objects.none()


    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if self.request.method in ['PATCH', 'PUT', 'DELETE']:
            if user.is_authenticated:
                if obj.user == user or user.is_staff or user.is_superuser or user.groups.filter(name="manager").exists():
                    return obj
                else:
                    raise PermissionDenied("You do not have permission to modify this booking.")
            else:
                raise PermissionDenied("Authentication required to modify bookings.")
        return obj
    # ------------------------
    # Public: Available Times
    # ------------------------
    @action(detail=False, methods=["get"], url_path="available-times")
    def available_times(self, request):
        date_str = request.GET.get("date")
        if not date_str:
            return Response(
                {"error": "Date query param is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        booked = Booking.objects.filter(
            reservation_date=date_str
        ).values_list("reservation_time", flat=True)

        available = [slot for slot, _ in TIME_SLOTS if slot not in booked]
        return Response({"times": available})

    # ------------------------
    # Send Emails
    # ------------------------
    def send_confirmation_email(self, booking):
        subject = "Your Table Reservation at Dhanno Banno Ki Rasoi"
        from_email = "Dhanno Banno Ki Rasoi <dhannobannokirasoi@gmail.com>"
        to_email = [booking.email]

        context = {
            "reservation_date": booking.reservation_date,
            "reservation_time": booking.reservation_time,
            "no_of_guests": booking.no_of_guests,
            "occasion": booking.occasion,
            "reference_number": booking.reference_number,
            "manage_link": f"{settings.FRONTEND_URL}/manage-reservation/{booking.reference_number}",
            "photo_link": f"{settings.BACKEND_URL}/static/img/bannocopy.jpg"
        }

        html_message = render_to_string("book_confirm.html", context)
        email_message = EmailMultiAlternatives(
            subject,
            strip_tags(html_message),
            from_email,
            to_email
        )
        email_message.attach_alternative(html_message, "text/html")
        email_message.send(fail_silently=False)

    def send_cancellation_email(self, booking):
        subject = "Your Reservation Has Been Cancelled"
        from_email = "Dhanno Banno Ki Rasoi <dhannobannokirasoi@gmail.com>"
        to_email = [booking.email]

        context = {
            "reservation_date": booking.reservation_date,
            "reservation_time": booking.reservation_time,
            "no_of_guests": booking.no_of_guests,
            "occasion": booking.occasion,
            "reference_number": booking.reference_number,
        }

        html_message = render_to_string("booking_cancelled.html", context)
        email_message = EmailMultiAlternatives(subject, strip_tags(html_message), from_email, to_email)
        email_message.attach_alternative(html_message, "text/html")
        email_message.send(fail_silently=False)

    # ------------------------
    # On Create: attach user if logged in
    # ------------------------
    def perform_create(self, serializer):
        email = self.request.data.get('email') or (
            self.request.user.email if self.request.user.is_authenticated else None
        )
        booking = serializer.save(
            user=self.request.user if self.request.user.is_authenticated else None,
            email=email
        )
        self.send_confirmation_email(booking)

    # ------------------------
    # Manage Booking by Reference Number
    # ------------------------
    @action(detail=False, methods=["get", "patch", "delete"], url_path="manage/(?P<ref>[^/.]+)")
    def manage_by_reference(self, request, ref):
        try:
            booking = Booking.objects.get(reference_number=ref)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == "GET":
            serializer = self.get_serializer(booking)
            return Response(serializer.data)

        elif request.method == "PATCH":
            serializer = self.get_serializer(booking, data=request.data, partial=True)
            if serializer.is_valid():
                updated_booking = serializer.save()
                self.send_confirmation_email(updated_booking)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == "DELETE":
            self.send_cancellation_email(booking)
            booking.delete()
            return Response({"message": "Booking cancelled successfully and email sent."}, status=status.HTTP_204_NO_CONTENT)

    

class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsManagerOrAdminForSafe]

    
class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['featured', 'category']
    search_fields = ['title', 'description', 'category__title']
    ordering_fields = ['price', 'title']
    # permission_classes = [IsManagerOrAdminForSafe]
    permission_classes = []

    


class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsManagerOrAdminForSafe]

#### FROM CARTS TO ORDERS
# CART VIEW, ORDERITEM VIEW, AND ORDER VIEW

class CartView(generics.ListCreateAPIView):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # if self.request.user.is_superuser:
        #     return Cart.objects.all()
        return Cart.objects.all().filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        Cart.objects.all().filter(user=self.request.user).delete()
        return Response("ok")


class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only allow the logged-in user to access their cart items
        # if self.request.user.is_superuser:
        #     return Cart.objects.all()
        return Cart.objects.filter(user=self.request.user)


    

class OrderView(generics.ListCreateAPIView):

    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
        
    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.filter(is_confirmed=True)  # ✅ Default: confirmed only

        if user.is_superuser:
            return Order.objects.all().order_by('-date')  # superuser sees all
        elif user.groups.count() == 0:
            return qs.filter(user=user).order_by('-date')  # customer sees only their confirmed orders
        elif user.groups.filter(name='Delivery Crew').exists():
            return qs.filter(delivery_crew=user).order_by('-date')  # delivery crew sees confirmed assigned orders
        else:
            return qs.order_by('-date')  # e.g., manager sees all confirmed orders

    def create(self, request, *args, **kwargs):
        user = request.user
        cart_items = Cart.objects.filter(user=user)
        menuitem_count = cart_items.count()
        if menuitem_count == 0:
            return Response({"message": "No item in cart"}, status=400)

        data = request.data.copy()
        total = self.get_total_price(user)
        data['total'] = total
        data['user'] = user.id

        # Accept delivery fields, defaulting to "ASAP" for time_slot if not given
        delivery_fields = [
            'delivery_type', 'delivery_address', 'delivery_city',
            'delivery_pin', 'delivery_time_slot'
        ]
        for field in delivery_fields:
            if field in request.data:
                data[field] = request.data.get(field)
            elif field == 'delivery_time_slot':
                data[field] = "ASAP"  # fallback default

        order_serializer = OrderSerializer(data=data)
        if order_serializer.is_valid():
            order = order_serializer.save()

            # Transfer cart items to order
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    menuitem=item.menuitem,
                    price=item.price,
                    quantity=item.quantity,
                )

            cart_items.delete()  # Empty the cart

            # ---- SEND CONFIRMATION EMAIL ----
        
            user_email = user.email
            if user_email:
                subject = f"Order Confirmation - Order #{order.id}"
                # Query all order items for this order
                order_items = OrderItem.objects.filter(order=order)
                user_profile = getattr(request.user, 'profile', None)
                gender = getattr(user_profile, 'gender', '').lower() if user_profile else ''
                address = "Chatoree" if gender == "f" else "Chatore"


                context = {
                    "user": request.user,
                    "order": order,
                    "order_items": order_items,
                    "address": address,  # Pass it in!
                    # "photo_link" :f"{settings.BACKEND_URL}/restaurante/static/img/banno2.png"
                    "photo_link" :f"{settings.BACKEND_URL}/static/img/banno2.png"
                }
            

                html_content = render_to_string('order_confirmation_email.html', context)
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body="Thank you for your order!",
                    from_email="Dhanno Banno Ki Rasoi <dhannobannokirasoi@gmail.com>",
                    to=[user_email],
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()

            # Return order data
            return Response(order_serializer.data)
        else:
            return Response(order_serializer.errors, status=400)

    def get_total_price(self, user):
        return sum(item.price for item in Cart.objects.filter(user=user))
    
@api_view(['GET'])
@permission_classes([AllowAny])
def available_time_slots(request):
    slots = [slot for slot, _ in DELIVERY_TIME_SLOTS]
    return Response({"time_slots": slots})


class SingleOrderView(generics.RetrieveUpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        order = self.get_object()

        # Prevent others from modifying another user's order
        if order.user != request.user:
            return Response({"error": "Unauthorized"}, status=403)

        # If normal customer (no group)
        if request.user.groups.count() == 0:
            # Allow PATCH for address fields only
            address_fields = ['delivery_address', 'delivery_city', 'delivery_pin']
            updated = False

            for field in address_fields:
                if field in request.data:
                    setattr(order, field, request.data[field])
                    updated = True

            if updated:
                order.save()
                print("📤 API /orders/<id> GET response:", OrderSerializer(order).data)
                return Response(OrderSerializer(order).data)
            else:
                return Response({"error": "Only address fields can be updated."}, status=400)

        # Else for admin/crew/manager, allow full update
        return super().update(request, *args, **kwargs)




###### USER REGISTRATION
# USER PFOFILE REGISTRATON RELATED


class UserViewSet(viewsets.ModelViewSet):
   queryset = User.objects.all().order_by('id')
   serializer_class = UserSerializer
   permission_classes = [IsAdminUser] 

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserWithProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
    
class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserWithProfileSerializer
    permission_classes = [IsAdminUser]
    
#####################
# GROUP PERMISSIONS BY MANAGERS AND ADMINISTRATORS

class GroupViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]
    def list(self, request):
        users = User.objects.all().filter(groups__name='Manager')
        items = UserSerializer(users, many=True)
        return Response(items.data)

    def create(self, request):
        user = get_object_or_404(User, username=request.data['username'])
        managers = Group.objects.get(name="Manager")
        managers.user_set.add(user)
        return Response({"message": "user added to the manager group"}, 200)

    def destroy(self, request):
        user = get_object_or_404(User, username=request.data['username'])
        managers = Group.objects.get(name="Manager")
        managers.user_set.remove(user)
        return Response({"message": "user removed from the manager group"}, 200)

class DeliveryCrewViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    def list(self, request):
        users = User.objects.all().filter(groups__name='Delivery Crew')
        items = UserSerializer(users, many=True)
        return Response(items.data)

    def create(self, request):
        #only for super admin and managers
        if self.request.user.is_superuser == False:
            if self.request.user.groups.filter(name='Manager').exists() == False:
                return Response({"message":"forbidden"}, status.HTTP_403_FORBIDDEN)
        
        user = get_object_or_404(User, username=request.data['username'])
        dc = Group.objects.get(name="Delivery Crew")
        dc.user_set.add(user)
        return Response({"message": "user added to the delivery crew group"}, 200)

    def destroy(self, request):
        #only for super admin and managers
        if self.request.user.is_superuser == False:
            if self.request.user.groups.filter(name='Manager').exists() == False:
                return Response({"message":"forbidden"}, status.HTTP_403_FORBIDDEN)
        user = get_object_or_404(User, username=request.data['username'])
        dc = Group.objects.get(name="Delivery Crew")
        dc.user_set.remove(user)
        return Response({"message": "user removed from the delivery crew group"}, 200)
    


class CustomerReviewViewSet(viewsets.ModelViewSet):
    queryset = CustomerReview.objects.select_related('user').order_by('-created_at')
    serializer_class = CustomerReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='my')
    def my_reviews(self, request):
        user_reviews = CustomerReview.objects.filter(user=request.user).order_by('-created_at')
        page = self.paginate_queryset(user_reviews)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(user_reviews, many=True)
        return Response(serializer.data)




# ################
# BOT ORDER EMAIL VIEW
############


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def botorder_confirm_email(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)

        order.is_confirmed = True  # ✅ Mark as confirmed
        order.save()

        # ✅ Clear related cache keys
        session_id = f"user_{request.user.id}"
        cache.delete(f"order_context_{session_id}")
        cache.delete(f"chat_history_{session_id}")


        order_items = OrderItem.objects.filter(order=order)

        user_profile = getattr(request.user, 'profile', None)
        gender = getattr(user_profile, 'gender', '').lower() if user_profile else ''
        address = "Chatoree" if gender == "f" else "Chatore"

        context = {
            "user": request.user,
            "order": order,
            "order_items": order_items,
            "address": address,
            "photo_link": f"{settings.BACKEND_URL}/static/img/banno2.png"
        }

        html_content = render_to_string('order_confirmation_email.html', context)
        msg = EmailMultiAlternatives(
            subject=f"Order Confirmation - Order #{order.id}",
            body="Thank you for your order!",
            from_email="Dhanno Banno Ki Rasoi <dhannobannokirasoi@gmail.com>",
            to=[request.user.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        # return Response({"message": "Confirmation email sent."})
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    
    except Order.DoesNotExist:
        return Response({"error": "Order not found or not authorized"}, status=404)
    
##############################
# DELETE UNCONFIRMED ORDER
##############################
from django.core.cache import cache
import json
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_unconfirmed_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)

        if order.is_confirmed:
            return Response({"error": "Cannot delete a confirmed order."}, status=400)

        order.delete()
        # ✅ Clear order_context from cache
        session_id = f"user_{request.user.id}"
        order_key = f"order_context_{session_id}"
        cache.delete(order_key)
        print(f"🧹 Cleared order_context for {session_id}")

        # Cache key
        chat_key = f"chat_history_user_{request.user.id}"
        history = cache.get(chat_key, [])

        # Append tool-style function message
        history.append({
            "role": "function",
            "name": "delete_order",
            "content": json.dumps({"message": f"❌ Order #{order_id} has been cancelled."})
        })

        # Append assistant follow-up message
        history.append({
            "role": "assistant",
            "content": f"✅ Aapka order #{order_id} cancel ho gaya bhaiya. Naya order shuru karna ho toh bataiye!"
        })

        # Save updated history
        cache.set(chat_key, history, timeout=600)


        return Response({"message": f"Order #{order_id} deleted."})
    
    except Order.DoesNotExist:
        return Response({"error": "Order not found or not authorized"}, status=404)




##################################
# JWT SUPPLMENT FOR TRANSFERRRING GUTEST CACHE TO USER
################################
# views.py

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.cache import cache

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        # 🔁 Migrate guest cache to user cache
        request = self.context.get("request")
        if request:
            guest_id = request.headers.get("X-Guest-Id")
            user = self.user

            if guest_id:
                guest_session_id = f"guest_{guest_id}"
                user_session_id = f"user_{user.id}"

                for key in ["chat_mode", "order_context", "booking_context", "lang_pref", "chat_history"]:
                    guest_key = f"{key}_{guest_session_id}"
                    user_key = f"{key}_{user_session_id}"

                    value = cache.get(guest_key)
                    if value:
                        cache.set(user_key, value, timeout=600)
                        cache.delete(guest_key)

        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
