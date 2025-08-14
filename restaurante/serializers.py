
from rest_framework import serializers
from .models import Booking, Category, MenuItem, Cart, Order, OrderItem, \
    UserProfile, hundred_years_ago, CustomerReview
from django.contrib.auth.models import User
from django.db import models
from datetime import date



class BookingSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = '__all__'

    def get_user(self, obj):
        if obj.user:
            return {
                "id": obj.user.id,
                "username": obj.user.username,
                "email": obj.user.email
            }
        return None

    # class Meta:
    #     model = Booking
    #     fields = '__all__'
    
    def validate(self, data):
        reservation_date = data.get('reservation_date', getattr(self.instance, 'reservation_date', None))
        reservation_time = data.get('reservation_time', getattr(self.instance, 'reservation_time', None))
        email = data.get('email', getattr(self.instance, 'email', None))

    # Only check for duplicates if creating or changing date/time/email
        existing = Booking.objects.filter(
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            email=email
    )

    # Exclude the current record if we're updating
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise serializers.ValidationError("A booking already exists for this time slot and email.")

        return data



class CategorySerializer (serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'title', 'slug']


class MenuItemSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all()
    )
    # category = CategorySerializer(read_only=True)
    class Meta:
        model = MenuItem
        fields = ['id', 'title', 'price', 'featured', 'description', 'image', 'category']



class CartSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault()
    )
    menuitem = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.all()
    )

    class Meta:
        model = Cart
        fields = ['id', 'user', 'menuitem', 'unit_price', 'quantity', 'price']
        extra_kwargs = {
            'unit_price': {'read_only': True},
            'price': {'read_only': True},
            'user': {'read_only': True},  # Disallow changing user on update
        }

    def create(self, validated_data):
        user = self.context['request'].user  # Always use current authenticated user
        menuitem = validated_data['menuitem']
        quantity = int(validated_data['quantity'])

        unit_price = menuitem.price  # Always get price from MenuItem model
        price = unit_price * quantity

        # Add or update the cart row for this user+menuitem
        cart_item, created = Cart.objects.update_or_create(
            user=user,
            menuitem=menuitem,
            defaults={
                'quantity': quantity,
                'unit_price': unit_price,
                'price': price,
            }
        )
        return cart_item

    def update(self, instance, validated_data):
        # Only allow changing quantity, not menuitem or user
        quantity = int(validated_data.get('quantity', instance.quantity))
        instance.quantity = quantity

        # Always use the current price from the MenuItem model
        unit_price = instance.menuitem.price
        instance.unit_price = unit_price
        instance.price = unit_price * quantity

        instance.save()
        return instance



class MenuItemShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ['title']  # or just ['title']

class OrderItemSerializer(serializers.ModelSerializer):
    menuitem= MenuItemShortSerializer(read_only=True)
    class Meta:
        model = OrderItem
        fields = ['order', 'menuitem', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    orderitem = OrderItemSerializer(many=True, read_only=True, source='order')

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'delivery_crew',
            'status',
            'date',
            'total',
            'orderitem',
            'delivery_type',
            'delivery_address',
            'delivery_city',
            'delivery_pin',
            'delivery_time_slot',
            'payment_method', 
            'payment_status', 
            'is_confirmed'
        ]


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'email', 'groups']

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user
    

class DefaultValueHandlingSerializer(serializers.ModelSerializer):
    DEFAULTS = {}

    def validate(self, attrs):
        for field, default in self.DEFAULTS.items():
            if attrs.get(field) in [None, '']:
                attrs[field] = default
        return super().validate(attrs)


class UserProfileSerializer(DefaultValueHandlingSerializer):
    
    DEFAULTS = {
        'dob': hundred_years_ago(),
        'gender': 'T',
        'city': 'Hajipur',
        'state': 'Bihar',
        'country': 'India',
        'marital_status': 'N',
        'education': 'LL',
        'income': 'B',
    }

    class Meta:
        model = UserProfile
        fields = [
            'dob', 'gender', 'city', 'state', 'country',
            'marital_status', 'education', 'income', 'phone'
        ]

    
class UserRegistrationSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'profile']

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        UserProfile.objects.create(user=user, **profile_data)
        return user

    
class UserWithProfileSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']
        read_only_fields = ['id', 'username']

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.save()

        profile = instance.profile
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()

        return instance




class CustomerReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    city = serializers.CharField(source='user.profile.city', read_only=True, default='')  # If city is in a profile

    class Meta:
        model = CustomerReview
        fields = [
            'id', 'feedback', 'rating', 'created_at', 'user', 'first_name', 'last_name', 'city'
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


