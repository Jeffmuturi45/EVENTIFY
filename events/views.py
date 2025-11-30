from django.shortcuts import render
from django.utils import timezone
from .models import Event, Category

def event_list(request):
    # Get all active events
    events = Event.objects.filter(is_active=True).order_by('start_date')
    categories = Category.objects.all()
    
    # Better event separation logic
    featured_events = events.filter(is_featured=True, is_coming_soon=False)
    coming_soon_events = events.filter(is_coming_soon=True)
    
    # Available events: active, not coming soon, and not sold out
    available_events = events.filter(
        is_coming_soon=False,
        is_active=True
    )
    
    context = {
        'events': events,
        'featured_events': featured_events,
        'coming_soon_events': coming_soon_events,
        'available_events': available_events,
        'categories': categories,
    }
    return render(request, 'event_list.html', context)