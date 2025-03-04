"""
URL configuration for LittleLemon project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from restaurante import views

from rest_framework.routers import DefaultRouter

# router = DefaultRouter()

# router.register(r'tables', views.BookingViewSet)
# router.register(r'users', views.UserViewSet)



# urlpatterns = [
#     path("admin/", admin.site.urls),
#     path("restaurante/", include('restaurante.urls')),
#     path('restaurante/booking/', include(router.urls)),
#     path('', include(router.urls))
# ]

# Router for BookingViewSet
booking_router = DefaultRouter()
booking_router.register(r'tables', views.BookingViewSet, basename='booking')

# Router for UserViewSet
user_router = DefaultRouter()
user_router.register(r'users', views.UserViewSet, basename='user')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('restaurante/', include('restaurante.urls')),
    path('restaurante/booking/', include(booking_router.urls)),
    path('accounts/', include(user_router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]