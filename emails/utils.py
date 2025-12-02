import os
from io import BytesIO
from datetime import datetime
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def generate_ticket_pdf(booking, payment):
    """Generate PDF ticket for a booking"""
    buffer = BytesIO()

    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    # Prepare story (content)
    story = []

    # Styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#340BED"),
        alignment=TA_CENTER,
        spaceAfter=30
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor("#E11616"),
        alignment=TA_CENTER,
        spaceAfter=20
    )

    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor("#060505"),
        spaceAfter=10
    )

    # Header with logo
    story.append(Paragraph("🎪 EVENTIFY", title_style))
    story.append(Paragraph("E-TICKET", subtitle_style))
    story.append(Spacer(1, 20))

    # Event Details
    story.append(Paragraph("<b>EVENT DETAILS</b>", styles['Heading2']))
    story.append(Spacer(1, 10))

    event_details = [
        ["Event:", f"<b>{booking.event.title}</b>"],
        ["Date:",
            f"<b>{booking.event.start_date.strftime('%A, %B %d, %Y')}</b>"],
        ["Time:", f"<b>{booking.event.start_date.strftime('%I:%M %p')}</b>"],
        ["Venue:", f"<b>{booking.event.venue}</b>"],
    ]

    for label, value in event_details:
        story.append(Paragraph(f"{label}", info_style))
        story.append(Paragraph(f"{value}", info_style))
        story.append(Spacer(1, 5))

    story.append(Spacer(1, 20))

    # Ticket Details
    story.append(Paragraph("<b>TICKET INFORMATION</b>", styles['Heading2']))
    story.append(Spacer(1, 10))

    ticket_details = [
        ["Ticket Type:", f"<b>{booking.get_ticket_type_display()} TICKET</b>"],
        ["Quantity:", f"<b>{booking.quantity} ticket(s)</b>"],
        ["Booking ID:", f"<b>#{booking.id}</b>"],
        ["Transaction ID:", f"<b>{payment.mpesa_receipt_number}</b>"],
    ]

    for label, value in ticket_details:
        story.append(Paragraph(f"{label}", info_style))
        story.append(Paragraph(f"{value}", info_style))
        story.append(Spacer(1, 5))

    story.append(Spacer(1, 20))

    # Customer Information
    story.append(Paragraph("<b>CUSTOMER INFORMATION</b>", styles['Heading2']))
    story.append(Spacer(1, 10))

    customer_details = [
        ["Name:",
            f"<b>{booking.user.get_full_name() or booking.user.username}</b>"],
        ["Email:", f"<b>{booking.user.email}</b>"],
        ["Booking Date:",
            f"<b>{booking.created_at.strftime('%Y-%m-%d %I:%M %p')}</b>"],
    ]

    for label, value in customer_details:
        story.append(Paragraph(f"{label}", info_style))
        story.append(Paragraph(f"{value}", info_style))
        story.append(Spacer(1, 5))

    story.append(Spacer(1, 20))

    # Price Summary
    story.append(Paragraph("<b>PRICE SUMMARY</b>", styles['Heading2']))
    story.append(Spacer(1, 10))

    price_data = [
        ["Description", "Amount"],
        ["Ticket Price", f"KSh {booking.unit_price}"],
        ["Quantity", f"{booking.quantity}"],
        ["Total Amount", f"<b>KSh {booking.total_price}</b>"],
        ["Payment Status", f"<b>{payment.get_status_display()}</b>"],
    ]

    price_table = Table(price_data, colWidths=[3*inch, 2*inch])
    price_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.gray),
    ]))

    story.append(price_table)
    story.append(Spacer(1, 30))

    # Footer Note
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.gray,
        alignment=TA_CENTER
    )

    story.append(Paragraph(
        "Present this e-ticket at the event entrance. "
        "For any inquiries, contact support@eventify.com",
        footer_style
    ))

    # Build PDF
    doc.build(story)

    # Get PDF value
    pdf = buffer.getvalue()
    buffer.close()

    return pdf


def format_phone_number(phone):
    """Format phone number to M-Pesa format (254XXXXXXXXX)"""
    if not phone:
        return None

    # Remove any spaces, dashes, or other characters
    phone = ''.join(filter(str.isdigit, phone))

    # Handle different formats
    if phone.startswith('0') and len(phone) == 10:
        # Format: 07XXXXXXXX or 01XXXXXXXX
        return '254' + phone[1:]
    elif phone.startswith('254') and len(phone) == 12:
        # Format: 2547XXXXXXXX or 2541XXXXXXXX
        return phone
    elif phone.startswith('7') and len(phone) == 9:
        # Format: 7XXXXXXXX
        return '254' + phone
    elif phone.startswith('1') and len(phone) == 9:
        # Format: 1XXXXXXXX (for 010... numbers)
        return '254' + phone
    else:
        return None


def send_ticket_email(booking, payment):
    """Send ticket email with PDF attachment"""
    try:
        # Generate PDF ticket
        pdf_content = generate_ticket_pdf(booking, payment)

        # Prepare email
        subject = f"🎫 Your Event Ticket: {booking.event.title}"

        # HTML email content
        html_content = render_to_string('ticket_email.html', {
            'booking': booking,
            'payment': payment,
            'user': booking.user,
        })

        # Text email content (fallback)
        text_content = f"""
        EVENTIFY - Your Ticket Confirmation
        
        Hello {booking.user.get_full_name() or booking.user.username},
        
        Thank you for your booking! Here are your ticket details:
        
        Event: {booking.event.title}
        Date: {booking.event.start_date.strftime('%A, %B %d, %Y')}
        Time: {booking.event.start_date.strftime('%I:%M %p')}
        Venue: {booking.event.venue}
        
        Ticket Type: {booking.get_ticket_type_display()}
        Quantity: {booking.quantity}
        Total Amount: KSh {booking.total_price}
        
        Your e-ticket is attached as a PDF. Please present it at the event entrance.
        
        Booking ID: #{booking.id}
        Transaction ID: {payment.mpesa_receipt_number}
        
        Thank you for choosing EVENTIFY!
        
        Best regards,
        EVENTIFY Team
        """

        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[booking.user.email],
            bcc=[settings.DEFAULT_FROM_EMAIL]  # Keep copy for admin
        )

        # Attach HTML content
        email.attach_alternative(html_content, "text/html")

        # Attach PDF
        email.attach(
            filename=f"ticket_{booking.id}_{booking.user.username}.pdf",
            content=pdf_content,
            mimetype="application/pdf"
        )

        # Send email
        email.send(fail_silently=False)

        return True, "Ticket email sent successfully!"

    except Exception as e:
        print(f"Error sending ticket email: {e}")
        return False, str(e)
