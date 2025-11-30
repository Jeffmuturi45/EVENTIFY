from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

# cretae your models here
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Event(models.Model):
    # Basic Information
    title = models.CharField(max_length=200)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True, help_text="Brief description for cards")
    image = models.ImageField(upload_to='event_images/', blank=True, null=True)
    
    # Category
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Date & Time
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Location
    venue = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Capacity & Pricing
    total_capacity = models.PositiveIntegerField(help_text="Total number of tickets available")
    tickets_sold = models.PositiveIntegerField(default=0)
    
    # Status Flags
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_coming_soon = models.BooleanField(default=False, help_text="Event not yet available for booking")
    
    # Coming soon details
    coming_soon_text = models.CharField(max_length=200, blank=True, default="Coming Soon")
    booking_opens_date = models.DateTimeField(blank=True, null=True, help_text="When booking becomes available")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_date']
    
    def __str__(self):
        return self.title
    
    def clean(self):
        # Validate dates
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date")
        
        if self.booking_opens_date and self.booking_opens_date > self.start_date:
            raise ValidationError("Booking opens date cannot be after event start date")
    
    @property
    def is_upcoming(self):
        return self.start_date > timezone.now()
    
    @property
    def is_ongoing(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date
    
    @property
    def is_past(self):
        return self.end_date < timezone.now()
    
    @property
    def available_tickets(self):
        return self.total_capacity - self.tickets_sold
    
    @property
    def is_sold_out(self):
        return self.tickets_sold >= self.total_capacity
    
    @property
    def can_book(self):
        """Check if event is available for booking"""
        if self.is_coming_soon:
            return False
        if self.booking_opens_date:
            return timezone.now() >= self.booking_opens_date
        return self.is_active and not self.is_sold_out and self.is_upcoming
    
    @property
    def days_until_event(self):
        """Days until event starts"""
        if self.is_past:
            return 0
        delta = self.start_date - timezone.now()
        return delta.days
    
    @property
    def status(self):
        """Get event status for display"""
        if self.is_coming_soon:
            return "coming_soon"
        elif self.is_sold_out:
            return "sold_out"
        elif self.is_past:
            return "past"
        elif self.is_ongoing:
            return "ongoing"
        else:
            return "available"

class TicketType(models.Model):
    TICKET_CATEGORIES = [
        ('free', 'Free'),
        ('regular', 'Regular'),
        ('vip', 'VIP'),
        ('vvip', 'VVIP'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_types')
    category = models.CharField(max_length=10, choices=TICKET_CATEGORIES, default='regular')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_available = models.PositiveIntegerField()
    description = models.TextField(blank=True, help_text="What's included in this ticket type")
    
    class Meta:
        unique_together = ['event', 'category']
    
    def __str__(self):
        return f"{self.event.title} - {self.get_category_display()}"
    
    @property
    def is_available(self):
        return self.quantity_available > 0