from django.shortcuts import render
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView, DestroyAPIView
from rest_framework import viewsets, permissions
from django.contrib.auth.models import User
from .serializers import MenuSerializer, BookingSerializer, UserSerializer
from .models import Menu, Booking

# Create your views here.

def index(request):
    return render(request, 'index.html', {})


class MenuItemsView(ListCreateAPIView):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer

class SingleMenuItemView(RetrieveUpdateAPIView, DestroyAPIView):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer


# Add code to create Menu model
class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated] 
    # permission_classes = [permissions.AllowAny] 

class UserViewSet(viewsets.ModelViewSet):
   queryset = User.objects.all().order_by('id')
   serializer_class = UserSerializer
   permission_classes = [permissions.IsAuthenticated] 
#    permission_classes = [permissions.AllowAny] 

