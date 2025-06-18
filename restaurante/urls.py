

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import index, CategoriesView, CartView, OrderView, SingleOrderView, GroupViewSet, DeliveryCrewViewSet, \
UserRegistrationView, UserProfileView, MenuItemViewSet, AdminUserViewSet, BookingViewSet, CartItemDetailView
from restaurante.views import available_time_slots
from .views import CustomerReviewViewSet



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
]


router = DefaultRouter()
router.register(r'menu-items', MenuItemViewSet, basename='menu')
router.register(r'admin/users', AdminUserViewSet, basename='admin-users')
router.register(r'booking', BookingViewSet, basename='booking')
router.register(r'customer-reviews', CustomerReviewViewSet, basename='customer-review')


urlpatterns += router.urls