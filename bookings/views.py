from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from events.models import Event, TicketType
from .models import Booking

# Create your views here.
@login_required
def create_booking(request, event_id):
    event = get_object_or_404(Event, id=event_id, is_active=True)
    
    # Check if event is available for booking
    if not event.can_book:
        messages.error(request, "This event is not available for booking.")
        return redirect('home')
    
    if request.method == 'POST':
        # Check if this is just a price calculation or actual booking
        if 'calculate' in request.POST:
            # Just show the calculated prices without creating booking
            context = {
                'event': event,
                'ticket_types': event.ticket_types.all(),
            }
            return render(request, 'create_booking.html', context)
        
        # Actual booking creation
        ticket_type = request.POST.get('ticket_type')
        quantity = request.POST.get('quantity')
        
        # Handle custom quantity
        if quantity == 'custom':
            custom_quantity = request.POST.get('custom_quantity')
            if not custom_quantity:
                messages.error(request, "Please enter a quantity.")
                context = {
                    'event': event,
                    'ticket_types': event.ticket_types.all(),
                }
                return render(request, 'create_booking.html', context)
            quantity = int(custom_quantity)
        else:
            quantity = int(quantity)
        
        # Validate quantity range
        if quantity < 1 or quantity > 10:
            messages.error(request, "Quantity must be between 1 and 10.")
            context = {
                'event': event,
                'ticket_types': event.ticket_types.all(),
            }
            return render(request, 'create_booking.html', context)
        
        # Validate ticket type and quantity
        try:
            ticket_info = event.ticket_types.get(category=ticket_type)
            if quantity > ticket_info.quantity_available:
                messages.error(request, f"Only {ticket_info.quantity_available} {ticket_type} tickets available.")
                context = {
                    'event': event,
                    'ticket_types': event.ticket_types.all(),
                }
                return render(request, 'create_booking.html', context)
        except TicketType.DoesNotExist:
            messages.error(request, "Invalid ticket type selected.")
            context = {
                'event': event,
                'ticket_types': event.ticket_types.all(),
            }
            return render(request, 'create_booking.html', context)
        
        # Create booking
        booking = Booking.objects.create(
            user=request.user,
            event=event,
            ticket_type=ticket_type,
            quantity=quantity,
            unit_price=ticket_info.price,
            total_price=ticket_info.price * quantity
        )
        
        messages.success(request, "Booking created successfully! Proceed to payment.")
        return redirect('process_payment', booking_id=booking.id)
    
    # GET request - show booking form
    context = {
        'event': event,
        'ticket_types': event.ticket_types.all(),
    }
    return render(request, 'create_booking.html', context)

@login_required
def booking_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    context = {
        'booking': booking,
    }
    return render(request, 'booking_success.html', context)

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'bookings': bookings,
    }
    return render(request, 'my_bookings.html', context)