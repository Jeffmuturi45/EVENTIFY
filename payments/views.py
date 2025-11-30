from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from datetime import datetime
from bookings.models import Booking
from .models import Payment
from .mpesa_utils import MpesaGateway

def format_phone_number(phone_number):
    """Format and validate Kenyan phone numbers"""
    if not phone_number:
        return None
    
    # Remove all whitespace and special characters
    phone = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Handle different Kenyan phone number formats
    if phone.startswith('+254'):
        phone = phone[1:]  # Remove the + sign
    elif phone.startswith('254'):
        pass  # Already in correct format
    elif phone.startswith('07') or phone.startswith('01'):
        phone = '254' + phone[1:]  # Replace leading 0 with 254
    else:
        return None
    
    # Validate length (254 + 9 digits = 12 characters)
    if len(phone) != 12 or not phone.isdigit():
        return None
    
    return phone

@login_required
def process_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if booking can proceed to payment
    if not booking.can_proceed_to_payment:
        messages.error(request, "This booking cannot proceed to payment. It may be expired or already paid.")
        return redirect('my_bookings')
    
    # Check if payment already exists for this booking
    existing_payment = Payment.objects.filter(booking=booking).first()
    if existing_payment:
        if existing_payment.status == 'successful':
            messages.info(request, "Payment already completed for this booking.")
            return redirect('payment_success', payment_id=existing_payment.id)
        elif existing_payment.status == 'pending':
            messages.info(request, "Payment already initiated for this booking. Checking status...")
            # Check current status instead of assuming success
            return redirect('payment_pending', payment_id=existing_payment.id)
    
    # Handle free tickets (amount = 0) - NO STK PUSH NEEDED
    if booking.total_price == 0:
        if request.method == 'POST' and 'free_ticket' in request.POST:
            return handle_free_ticket(request, booking)
        else:
            context = {'booking': booking}
            return render(request, 'process_payment.html', context)
    
    # PAID TICKETS - Process real payment
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        
        if not phone_number:
            messages.error(request, "Please enter your phone number.")
            return redirect('process_payment', booking_id=booking_id)
        
        # Format phone number
        formatted_phone = format_phone_number(phone_number)
        if not formatted_phone:
            messages.error(request, "Please enter a valid Kenyan phone number.")
            return redirect('process_payment', booking_id=booking_id)
        
        # Create payment record - STATUS REMAINS 'pending'
        payment = Payment.objects.create(
            booking=booking,
            user=request.user,
            phone_number=formatted_phone,
            amount=booking.total_price,
            status='pending'  # Explicitly set to pending
        )
        
        # INITIATE REAL STK PUSH
        mpesa = MpesaGateway()
        account_reference = f"EVENT{booking.id:06d}"
        transaction_desc = f"Tickets for {booking.event.title}"
        
        response, error = mpesa.stk_push(
            phone_number=formatted_phone,
            amount=booking.total_price,
            account_reference=account_reference,
            transaction_desc=transaction_desc
        )
        
        if error:
            # STK Push failed
            payment.status = 'failed'
            payment.save()
            messages.error(request, f"Failed to initiate payment: {error}")
            return redirect('payment_failed', payment_id=payment.id)
        
        # STK Push initiated successfully
        if response and response.get('ResponseCode') == '0':
            # Save M-Pesa request IDs
            payment.merchant_request_id = response.get('MerchantRequestID', '')
            payment.checkout_request_id = response.get('CheckoutRequestID', '')
            payment.save()
            
            messages.info(request, 
                "STK Push initiated! Check your phone for M-Pesa prompt. "
                "Payment status will update automatically."
            )
            
            # Redirect to pending payment page
            return redirect('payment_pending', payment_id=payment.id)
        else:
            # STK Push failed
            payment.status = 'failed'
            payment.save()
            error_message = response.get('errorMessage', 'Payment initiation failed') if response else 'Payment initiation failed'
            messages.error(request, f"Payment failed: {error_message}")
            return redirect('payment_failed', payment_id=payment.id)
    
    context = {'booking': booking}
    return render(request, 'process_payment.html', context)

def handle_free_ticket(request, booking):
    """Handle free tickets (amount = 0) without payment - NO STK PUSH"""
    # Check if payment already exists
    existing_payment = Payment.objects.filter(booking=booking).first()
    if existing_payment:
        messages.info(request, "Free ticket already confirmed!")
        return redirect('payment_success', payment_id=existing_payment.id)
    
    # Create payment record with zero amount - NO STK PUSH
    payment = Payment.objects.create(
        booking=booking,
        user=request.user,
        phone_number='FREE',
        amount=0,
        status='successful',  # Auto-confirm free tickets
        mpesa_receipt_number=f"FREE{booking.id:06d}"
    )
    
    # Update booking status
    booking.status = 'confirmed'
    booking.save()
    
    messages.success(request, "Free ticket confirmed successfully! No payment required.")
    return redirect('payment_success', payment_id=payment.id)

def check_transaction_status(self, checkout_request_id):
    """Check M-Pesa transaction status"""
    access_token = self.get_access_token()
    if not access_token:
        return None, "Failed to get access token"

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query"

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = self.generate_password(timestamp)

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    payload = {
        "BusinessShortCode": self.shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return data, None
    except requests.exceptions.RequestException as e:
        print(f"Error checking transaction: {e}")
        return None, str(e)

@login_required
def payment_pending(request, payment_id):
    """Show pending payment page and check real status"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    # Check current status
    if payment.status == 'successful':
        messages.success(request, "Payment confirmed successfully!")
        return redirect('payment_success', payment_id=payment.id)
    elif payment.status == 'failed':
        messages.error(request, "Payment failed. Please try again.")
        return redirect('payment_failed', payment_id=payment.id)
    
    # For pending payments, check M-Pesa status
    if payment.status == 'pending' and payment.checkout_request_id:
        status, message = payment.check_mpesa_status()
        if status == 'successful':
            messages.success(request, "Payment confirmed successfully!")
            return redirect('payment_success', payment_id=payment.id)
        elif status == 'failed':
            messages.error(request, f"Payment failed: {message}")
            return redirect('payment_failed', payment_id=payment.id)
    
    context = {'payment': payment}
    return render(request, 'payment_pending.html', context)

@login_required
def payment_success(request, payment_id):
    """Show payment success page - ONLY if payment is actually successful"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    # Check actual payment status - don't auto-update to successful
    if payment.status == 'pending':
        # Check M-Pesa status for pending payments
        status, message = payment.check_mpesa_status()
        if status == 'failed':
            messages.error(request, "Payment was cancelled or failed. Please try again.")
            return redirect('payment_failed', payment_id=payment.id)
        elif status != 'successful':
            # Still pending or failed
            messages.info(request, "Payment is still processing. Please wait for confirmation.")
            return redirect('payment_pending', payment_id=payment.id)
    
    # Only show success if payment is actually successful
    if payment.status != 'successful':
        messages.error(request, "Payment not confirmed. Please complete the payment.")
        return redirect('process_payment', booking_id=payment.booking.id)
    
    context = {
        'payment': payment,
        'booking': payment.booking,
    }
    return render(request, 'payment_successful.html', context)

# M-Pesa Callback Handler (for production)
@csrf_exempt
def mpesa_callback(request):
    """Handle M-Pesa STK Push callback - for production use"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("M-Pesa Callback Received:", data)
            
            # Extract callback metadata
            callback_metadata = data.get('Body', {}).get('stkCallback', {})
            checkout_request_id = callback_metadata.get('CheckoutRequestID')
            result_code = callback_metadata.get('ResultCode')
            result_desc = callback_metadata.get('ResultDesc')
            
            # Find payment by checkout request ID
            try:
                payment = Payment.objects.get(checkout_request_id=checkout_request_id)
                payment.callback_received = True
                payment.result_code = result_code
                payment.result_desc = result_desc
                payment.callback_data = data
                
                if result_code == 0:
                    # Payment successful
                    payment.status = 'successful'
                    
                    # Extract M-Pesa receipt number
                    callback_items = callback_metadata.get('CallbackMetadata', {}).get('Item', [])
                    for item in callback_items:
                        if item.get('Name') == 'MpesaReceiptNumber':
                            payment.mpesa_receipt_number = item.get('Value')
                        elif item.get('Name') == 'TransactionDate':
                            transaction_date = item.get('Value')
                            # Convert M-Pesa date format to datetime
                            try:
                                payment.transaction_date = timezone.make_aware(
                                    datetime.strptime(str(transaction_date), '%Y%m%d%H%M%S')
                                )
                            except:
                                payment.transaction_date = timezone.now()
                    
                    # Update booking status
                    booking = payment.booking
                    booking.status = 'confirmed'
                    booking.save()
                    
                else:
                    # Payment failed
                    payment.status = 'failed'
                
                payment.save()
                
            except Payment.DoesNotExist:
                print(f"Payment not found for checkout request: {checkout_request_id}")
            
            # Always return success to M-Pesa
            return JsonResponse({
                "ResultCode": 0,
                "ResultDesc": "Success"
            })
            
        except Exception as e:
            print(f"Error processing callback: {e}")
            return JsonResponse({
                "ResultCode": 1,
                "ResultDesc": "Failed"
            })
    
    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def payment_failed(request, payment_id):
    """Show payment failed page"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    context = {
        'payment': payment,
    }
    return render(request, 'payment_failed.html', context)