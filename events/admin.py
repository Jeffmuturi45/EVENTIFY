from django.contrib import admin
from .models import Event, Category, TicketType

# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'venue', 'start_date', 'status', 'is_featured', 'available_tickets', 'can_book']
    list_filter = ['is_active', 'is_featured', 'is_coming_soon', 'start_date', 'category']
    search_fields = ['title', 'venue', 'description']
    date_hierarchy = 'start_date'
    readonly_fields = ['tickets_sold', 'status']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'short_description', 'image', 'category')
        }),
        ('Date & Time', {
            'fields': ('start_date', 'end_date')
        }),
        ('Location', {
            'fields': ('venue', 'address', 'city')
        }),
        ('Capacity', {
            'fields': ('total_capacity', 'tickets_sold')
        }),
        ('Status & Visibility', {
            'fields': ('is_active', 'is_featured', 'is_coming_soon')
        }),
        ('Coming Soon Settings', {
            'fields': ('coming_soon_text', 'booking_opens_date'),
            'classes': ('collapse',)
        }),
    )

@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ['event', 'category', 'price', 'quantity_available', 'is_available']
    list_filter = ['category', 'event']
    search_fields = ['event__title']