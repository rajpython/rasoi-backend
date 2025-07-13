from django.contrib import admin
from . import models
from django.http import HttpResponse
import csv

# Register your models here.
admin.site.register(models.Category)
admin.site.register(models.CustomerReview)
admin.site.register(models.MenuItem)
admin.site.register(models.Booking)
admin.site.register(models.Cart)
admin.site.register(models.Order)
admin.site.register(models.OrderItem)
admin.site.register(models.UserProfile)



@admin.action(description="Export selected to CSV")
def export_as_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=chat_history.csv'
    writer = csv.writer(response)
    writer.writerow(['User', 'Session ID', 'Role', 'Message', 'Timestamp'])
    for obj in queryset:
        writer.writerow([
            obj.user.username if obj.user else 'Anonymous',
            obj.session_id,
            obj.role,
            obj.message,
            obj.timestamp.strftime("%Y-%m-%d %H:%M")
        ])
    return response



@admin.register(models.ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_id', 'role', 'short_message', 'timestamp')
    list_filter = ('role', 'timestamp')
    search_fields = ('user__username', 'session_id', 'message')
    actions = [export_as_csv]

    def short_message(self, obj):
        return (obj.message[:50] + '...') if len(obj.message) > 50 else obj.message
    short_message.short_description = 'Message'
