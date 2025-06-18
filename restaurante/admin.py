from django.contrib import admin

# Register your models here.

from . import models
# Register your models here.
admin.site.register(models.Category)
admin.site.register(models.CustomerReview)
admin.site.register(models.MenuItem)
admin.site.register(models.Booking)
admin.site.register(models.Cart)
admin.site.register(models.Order)
admin.site.register(models.OrderItem)
admin.site.register(models.UserProfile)
