from django.db import models
from django.contrib.auth.models import User
from datetime import date
import uuid
from django.utils import timezone
from django.conf import settings

def today():
    return timezone.now().date()

# Utility: Choices for time slots (11:00 to 20:00 with 30-min intervals)
TIME_SLOTS = [
    (f"{hour:02d}:{minute:02d}", f"{hour:02d}:{minute:02d}")
    for hour in range(11, 20)
    for minute in (0, 30)
] + [("20:00", "20:00")]

DELIVERY_TIME_SLOTS = [("ASAP", "ASAP")] + TIME_SLOTS


class Booking(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,    # if user deleted, booking stays
        null=True, blank=True,        # allow legacy data & anonymous bookings
        related_name='bookings'
    )
    reservation_date = models.DateField()
    reservation_time = models.CharField(max_length=5, choices=TIME_SLOTS,default="11:00")  # e.g., "17:30"
    no_of_guests = models.PositiveSmallIntegerField(default=1)
    occasion = models.CharField(max_length=50, choices=[
        ("Birthday", "Birthday"),
        ("Anniversary", "Anniversary"),
        ("Other", "Other")
    ],default="Birthday")
    email = models.EmailField(null=True, blank=True)
    # reference_number = models.CharField(max_length=12, unique=True, editable=False)
    reference_number = models.CharField(
    max_length=12,
    unique=True,
    null=True,
    blank=True,
    editable=False
)


    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = uuid.uuid4().hex[:12].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reservation_date} at {self.reservation_time} ({self.no_of_guests} guests)"
    

   

class Category(models.Model):
    slug = models.SlugField()
    title = models.CharField(max_length=255, db_index=True)

    def __str__(self):
        return self.title

class MenuItem(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, db_index=True)
    featured = models.BooleanField(db_index=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='menu_images/', null=True, blank=True)  # ✅ image field
    category = models.ForeignKey(Category, on_delete=models.PROTECT)

    def __str__(self):
        return self.title

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    #To switch to the following if one needs to allow for anonymous users
    # user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    menuitem = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.SmallIntegerField()
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        unique_together = ('menuitem', 'user')

    def __str__(self):
        return self.user.username


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    delivery_crew = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name="delivery_crew", null=True)
    status = models.BooleanField(default=0, db_index=True)
    total = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    # date = models.DateField(db_index=True)
    date = models.DateField(db_index=True, default=today)

    # Delivery/Pickup fields:
    delivery_type = models.CharField(
        max_length=10,
        choices=[('pickup', 'Pickup'), ('delivery', 'Delivery')],
        default='delivery'
    )
    delivery_address = models.CharField(max_length=255, blank=True, null=True)
    delivery_city = models.CharField(max_length=100, blank=True, null=True)
    delivery_pin = models.CharField(max_length=12, blank=True, null=True)
    delivery_time_slot = models.CharField(max_length=20,choices=DELIVERY_TIME_SLOTS,default="ASAP")

    payment_method = models.CharField(
    max_length=20,
    choices=[('stripe', 'Stripe'), ('cod', 'Cash on Delivery')],
    default='cod'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('paid', 'Paid')],
        default='pending'
    )
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)




    def __str__(self):
        return str(self.id)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='order')
    #switch to below to avoid cofusiom
    # order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')

    menuitem = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.SmallIntegerField()
    price = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        unique_together = ('order', 'menuitem')

# User profie addition at a later stage

def hundred_years_ago():
    today = date.today()
    try:
        return today.replace(year=today.year - 100)
    except ValueError:
        return today.replace(month=2, day=28, year=today.year - 100)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    dob = models.DateField(default= hundred_years_ago)

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('B', 'Bisexual'),
        ('T', 'Transgender'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='T', blank=True)

    city = models.CharField(max_length=100, default='Deoria', blank=True)
    state = models.CharField(max_length=100, default='UP', blank=True)
    country = models.CharField(max_length=100, default='India', blank=True)

    MARITAL_STATUS = [
        ('M', 'Married'),
        ('U', 'Unmarried'),
        ('N', 'Not Applicable')
    ]
    marital_status = models.CharField(max_length=1, choices=MARITAL_STATUS, default='N', blank=True)

    EDUCATION_LEVEL = [
        ('LL', 'Likh Lodha Padh Patthar'),
        ('BH', 'Below High School'),
        ('HS', 'High School'),
        ('BS', 'Bachelor’s Degree'),
        ('GD', 'Graduate Degree'),
    ]
    education = models.CharField(max_length=2, choices=EDUCATION_LEVEL, default='LL', blank=True)

    INCOME_RANGE = [
        ('B', 'Bhikhari'),
        ('L', 'Below $100K'),
        ('M', '$100K-$200K'),
        ('H', 'Above $200K'),
    ]
    income = models.CharField(max_length=1, choices=INCOME_RANGE, default='B', blank=True)

    phone = models.CharField(max_length=15, blank=True, default="")


    def __str__(self):
        return f"Profile for {self.user.username}"
    

class CustomerReview(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    feedback = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)  # 1 to 5 stars (optional)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}: {self.feedback[:30]}..."

### ADDED TO INCLUDE CHAT HISTORY 
# class ChatHistory(models.Model):
#     user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
#     session_id = models.CharField(max_length=100, null=True, blank=True)
#     role = models.CharField(max_length=20, choices=[('user', 'User'), ('assistant', 'Assistant')])
#     message = models.TextField()
#     timestamp = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         user_str = self.user.username if self.user else f"Session {self.session_id}"
#         return f"{self.role} - {user_str} - {self.timestamp}"
    

from django.contrib.postgres.fields import JSONField  # for PostgreSQL, or use models.JSONField in Django 3.1+

class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    role = models.CharField(
        max_length=20, 
        choices=[
            ('user', 'User'), 
            ('assistant', 'Assistant'),
            ('function', 'Function')
        ]
    )
    message = models.TextField(blank=True, null=True)
    function_name = models.CharField(max_length=100, blank=True, null=True)
    function_arguments = models.JSONField(blank=True, null=True)
    function_result = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_str = self.user.username if self.user else f"Session {self.session_id}"
        return f"{self.role} - {user_str} - {self.timestamp}"



