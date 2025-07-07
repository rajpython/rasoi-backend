from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         UserProfile.objects.create(user=instance)

# # in restaurante/signals.py
# from django.conf import settings
# # from django.dispatch import receiver
# from djoser.signals import password_reset
# from djoser import utils

# @receiver(password_reset)
# def password_reset_email_handler(sender, user, context, **kwargs):
#     context['frontend_url'] = settings.FRONTEND_URL
