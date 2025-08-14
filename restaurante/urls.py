

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import index, CategoriesView, CartView, OrderView, SingleOrderView, GroupViewSet, DeliveryCrewViewSet, \
UserRegistrationView, UserProfileView, MenuItemViewSet, AdminUserViewSet, BookingViewSet, CartItemDetailView, delete_unconfirmed_order
from restaurante.views import available_time_slots
from .views import CustomerReviewViewSet
from .views import botorder_email
from .stripe_payment import CreatePaymentIntent

# from restaurante.chaatgpt_views_booking import chaatgpt_view
# from restaurante.chaatgpt_views_orders import chaatgpt_view
from .chatviews.chatbot_views import chaatgpt_view
from .chatviews.chaatgpt_reset import reset_chat_context




app_name = 'restaurante'


urlpatterns = [
    path('', index, name='index'),
    path('categories', CategoriesView.as_view()),
    path('cart/menu-items', CartView.as_view(), name='cart-list-create'),
    path('cart/menu-items/<int:pk>', CartItemDetailView.as_view(), name='cart-detail'),
    path('orders', OrderView.as_view()),
    path('orders/available-time-slots/', available_time_slots, name='order-available-time-slots'),
    path('orders/<int:pk>', SingleOrderView.as_view()),
    path('groups/manager/users', GroupViewSet.as_view({'get': 'list', 'post': 'create', 'delete': 'destroy'})),
    path('groups/delivery-crew/users', DeliveryCrewViewSet.as_view({'get': 'list', 'post': 'create', 'delete': 'destroy'})),
    # path('', include(router.urls)),  # ✅ Include the registered menu-items route
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('api/create-payment-intent/', CreatePaymentIntent.as_view(), name='create-payment-intent'),
    path('api/chaatbaat/', chaatgpt_view, name='chaatgpt'),
    path('api/chaatreset/', reset_chat_context, name='reset-chat-context'),
    path("orders/<int:order_id>/confirm/", botorder_email),
    path('orders/<int:order_id>/delete/', delete_unconfirmed_order, name='delete_unconfirmed_order'),
]


router = DefaultRouter()
router.register(r'menu-items', MenuItemViewSet, basename='menu')
router.register(r'admin/users', AdminUserViewSet, basename='admin-users')
router.register(r'booking', BookingViewSet, basename='booking')
router.register(r'customer-reviews', CustomerReviewViewSet, basename='customer-review')


urlpatterns += router.urls