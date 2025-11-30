from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    TICKET_TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('vip', 'VIP'), 
        ('vvip', 'VVIP'),
    ]
    
    # Basic Information
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='bookings')
    
    # Ticket Details
    ticket_type = models.CharField(max_length=10, choices=TICKET_TYPE_CHOICES)
    quantity = models.PositiveIntegerField(default=1)
    
    # Pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(help_text="Booking expires if not paid within time limit")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.event.title} - {self.quantity}x {self.ticket_type}"
    
    def save(self, *args, **kwargs):
        # Set expiry time (e.g., 30 minutes from creation)
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=30)
        
        # Calculate total price
        if self.unit_price and self.quantity:
            self.total_price = self.unit_price * self.quantity
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def can_proceed_to_payment(self):
        return self.status == 'pending' and not self.is_expired
    
class BookingManager(models.Manager):
    def confirmed(self):
        return self.filter(status='confirmed')
    
    def pending(self):
        return self.filter(status='pending')
    
    def upcoming(self):
        from django.utils import timezone
        return self.filter(
            status='confirmed',
            event__start_date__gt=timezone.now()
        )