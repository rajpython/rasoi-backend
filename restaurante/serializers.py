
from rest_framework import serializers
from .models import Menu, Booking
from django.contrib.auth.models import User


class MenuSerializer(serializers.ModelSerializer):

    class Meta:
        model = Menu
        fields = '__all__'


class BookingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Booking
        fields = '__all__'

# class UserSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = User
#         fields = ['url', 'username', 'password', 'email', 'groups']

from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['url', 'username', 'password', 'email', 'groups']

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user
