from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import Group, User


from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework import generics, viewsets, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny, IsAuthenticatedOrReadOnly

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




class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [AllowAny]

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
    # DRY: Send Confirmation Email
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
            # "manage_link": f"http://localhost:3000/manage-reservation/{booking.reference_number}"
            "manage_link": f"{settings.FRONTEND_URL}/manage-reservation/{booking.reference_number}",
            "photo_link" :f"{settings.BACKEND_URL}/restaurante/static/img/bannocopy.jpg"
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
    # On Create: Save + Send Email
    # ------------------------
    def perform_create(self, serializer):
        email = self.request.data.get('email') or (
            self.request.user.email if self.request.user.is_authenticated else None
        )
        booking = serializer.save(email=email)
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
        if user.is_superuser:
            return Order.objects.all()
        elif user.groups.count() == 0:  # normal customer - no group
            return Order.objects.filter(user=user)
        elif user.groups.filter(name='Delivery Crew').exists():
            return Order.objects.filter(delivery_crew=user)
        else:  # manager or delivery-crew
            return Order.objects.all()

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
                    "photo_link" :f"{settings.BACKEND_URL}/restaurante/static/img/banno2.png"
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
        if self.request.user.groups.count()==0: # Normal user, not belonging to any group = Customer
            return Response('Not Ok')
        else: #everyone else - Super Admin, Manager and Delivery Crew
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
