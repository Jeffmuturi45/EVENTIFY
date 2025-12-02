from django.shortcuts import render
from io import BytesIO

# Create your views here.
def generate_ticket_pdf(booking, payment):
    """Generate simple PDF ticket for a booking"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Title
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width/2, height-100, "🎪 EVENTIFY")
    p.setFont("Helvetica", 18)
    p.drawCentredString(width/2, height-130, "E-TICKET")
    
    # Event Details
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, height-180, "EVENT DETAILS:")
    p.setFont("Helvetica", 12)
    
    details = [
        f"Event: {booking.event.title}",
        f"Date: {booking.event.start_date.strftime('%A, %B %d, %Y')}",
        f"Time: {booking.event.start_date.strftime('%I:%M %p')}",
        f"Venue: {booking.event.venue}",
    ]
    
    y = height-210
    for detail in details:
        p.drawString(120, y, detail)
        y -= 25
    
    # Ticket Information
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y-30, "TICKET INFORMATION:")
    p.setFont("Helvetica", 12)
    
    ticket_info = [
        f"Ticket Type: {booking.get_ticket_type_display()}",
        f"Quantity: {booking.quantity}",
        f"Booking ID: #{booking.id}",
        f"Transaction ID: {payment.mpesa_receipt_number}",
    ]
    
    y -= 60
    for info in ticket_info:
        p.drawString(120, y, info)
        y -= 25
    
    # Customer Information
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y-30, "CUSTOMER INFORMATION:")
    p.setFont("Helvetica", 12)
    
    customer_info = [
        f"Name: {booking.user.get_full_name() or booking.user.username}",
        f"Email: {booking.user.email}",
        f"Booking Date: {booking.created_at.strftime('%Y-%m-%d %I:%M %p')}",
    ]
    
    y -= 60
    for info in customer_info:
        p.drawString(120, y, info)
        y -= 25
    
    # Price Summary
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y-30, "PRICE SUMMARY:")
    p.setFont("Helvetica", 12)
    
    price_info = [
        f"Ticket Price: KSh {booking.unit_price}",
        f"Quantity: {booking.quantity}",
        f"Total Amount: KSh {booking.total_price}",
        f"Payment Status: {payment.get_status_display()}",
    ]
    
    y -= 60
    for info in price_info:
        p.drawString(120, y, info)
        y -= 25
    
    # Footer
    p.setFont("Helvetica-Oblique", 10)
    p.drawCentredString(width/2, 50, "Present this ticket at the event entrance.")
    p.drawCentredString(width/2, 35, "For inquiries: support@eventify.com")
    
    p.showPage()
    p.save()
    
    pdf = buffer.getvalue()
    buffer.close()
    return pdf