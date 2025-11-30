from django.contrib import admin
from .models import Payment

# reister the Payment model in the admin interface
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'booking', 'amount', 'status', 'phone_number', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'phone_number', 'mpesa_receipt_number']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'booking')