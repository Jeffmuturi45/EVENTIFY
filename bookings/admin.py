from django.contrib import admin
from .models import Booking

# Register your models here.
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'ticket_type', 'quantity', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'ticket_type', 'created_at']
    search_fields = ['user__username', 'event__title']
    readonly_fields = ['created_at', 'updated_at', 'expires_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'event')