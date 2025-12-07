from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from bookings.models import Booking
from .models import Payment
from .mpesa_utils import MpesaGateway
from emails.utils import send_ticket_email, format_phone_number


@login_required
def process_payment(request, booking_id):
    """Show payment form and process payments"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    # Check if booking can proceed to payment
    if not booking.can_proceed_to_payment:
        messages.error(
            request, "This booking cannot proceed to payment. It may be expired or already paid.")
        return redirect('my_bookings')

    # Check if payment already exists for this booking
    try:
        existing_payment = Payment.objects.get(booking=booking)
        if existing_payment.status == 'successful':
            messages.info(
                request, "Payment already completed for this booking.")
            return redirect('payment_success', payment_id=existing_payment.id)
        elif existing_payment.status == 'pending':
            messages.info(
                request, "Payment already initiated for this booking. Checking status...")
            return redirect('payment_pending', payment_id=existing_payment.id)
        elif existing_payment.status == 'failed':
            messages.info(
                request, "Previous payment failed. You can retry below.")
    except Payment.DoesNotExist:
        existing_payment = None

    # Handle free tickets (amount = 0) - NO STK PUSH NEEDED
    if booking.total_price == 0:
        if request.method == 'POST' and 'free_ticket' in request.POST:
            return handle_free_ticket(request, booking, existing_payment)
        else:
            # Show free ticket confirmation page
            context = {'booking': booking}
            return render(request, 'process_payment.html', context)

    # PAID TICKETS - Show payment form (GET request)
    if request.method == 'GET':
        context = {'booking': booking}
        return render(request, 'process_payment.html', context)

    # PAID TICKETS - Process payment (POST request)
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')

        if not phone_number:
            messages.error(request, "Please enter your phone number.")
            return redirect('process_payment', booking_id=booking_id)

        # Format phone number
        formatted_phone = format_phone_number(phone_number)
        if not formatted_phone:
            messages.error(
                request, "Please enter a valid Kenyan phone number.")
            return redirect('process_payment', booking_id=booking_id)

        # Use existing payment if available and failed, otherwise create new one
        if existing_payment and existing_payment.status == 'failed':
            payment = existing_payment
            # Update payment details for retry
            payment.phone_number = formatted_phone
            payment.amount = booking.total_price
            payment.status = 'pending'
            payment.merchant_request_id = ''
            payment.checkout_request_id = ''
            payment.mpesa_receipt_number = ''
            payment.transaction_date = None
            payment.callback_received = False
            payment.result_code = None
            payment.result_desc = ''
            payment.callback_data = None
        else:
            # Create new payment record
            payment = Payment.objects.create(
                booking=booking,
                user=request.user,
                phone_number=formatted_phone,
                amount=booking.total_price,
                status='pending'
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
                          "Please enter your PIN to complete payment."
                          )

            # Redirect to pending payment page
            return redirect('payment_pending', payment_id=payment.id)
        else:
            # STK Push failed
            payment.status = 'failed'
            payment.save()
            error_message = response.get(
                'errorMessage', 'Payment initiation failed') if response else 'Payment initiation failed'
            messages.error(request, f"Payment failed: {error_message}")
            return redirect('payment_failed', payment_id=payment.id)


def handle_free_ticket(request, booking, existing_payment=None):
    """Handle free tickets (amount = 0) without payment"""
    # Use existing payment if available, otherwise create new one
    if existing_payment:
        payment = existing_payment
        # Update payment details for free ticket
        payment.phone_number = 'FREE'
        payment.amount = 0
        payment.status = 'successful'
        payment.mpesa_receipt_number = f"FREE{booking.id:06d}"
        payment.merchant_request_id = ''
        payment.checkout_request_id = ''
        payment.transaction_date = timezone.now()
        payment.callback_received = False
        payment.result_code = None
        payment.result_desc = ''
        payment.callback_data = None
    else:
        # Create payment record with zero amount
        payment = Payment.objects.create(
            booking=booking,
            user=request.user,
            phone_number='FREE',
            amount=0,
            status='successful',
            mpesa_receipt_number=f"FREE{booking.id:06d}",
            transaction_date=timezone.now()
        )

    # Update booking status
    booking.status = 'confirmed'
    booking.save()
    payment.save()

    # SEND TICKET EMAIL FOR FREE TICKET
    try:
        success, message = send_ticket_email(booking, payment)
        if success:
            messages.success(
                request, f"Free ticket confirmed! Ticket sent to {booking.user.email}!")
        else:
            messages.warning(
                request, f"Free ticket confirmed but email failed: {message}")
    except Exception as e:
        messages.success(request, "Free ticket confirmed successfully!")

    return redirect('payment_success', payment_id=payment.id)


@login_required
def payment_pending(request, payment_id):
    """Show pending payment page and check M-Pesa status - NO JS version"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)

    # If payment is already successful, redirect to success
    if payment.status == 'successful':
        return redirect('payment_success', payment_id=payment.id)

    # If payment already failed, redirect to failed page
    if payment.status == 'failed':
        return redirect('payment_failed', payment_id=payment.id)

    # At this point, payment.status == 'pending'
    # Try checking M-Pesa status (STK query)
    if payment.checkout_request_id:
        mpesa = MpesaGateway()
        status_data, error = mpesa.check_transaction_status(
            payment.checkout_request_id)

        if status_data:
            # Update payment status based on STK query result
            # 'successful', 'failed', or 'pending'
            new_status = status_data['status']
            payment.status = new_status
            payment.result_desc = status_data.get('message', '')
            payment.save()

            # If payment is now successful, send ticket email and redirect
            if new_status == 'successful':
                booking = payment.booking
                try:
                    send_ticket_email(booking, payment)
                except Exception:
                    pass  # Fail silently for email
                return redirect('payment_success', payment_id=payment.id)

            # If payment failed, redirect to failed page
            elif new_status == 'failed':
                return redirect('payment_failed', payment_id=payment.id)

        # If still pending (e.g., 4999), continue to render pending page

    context = {
        'payment': payment,
    }
    return render(request, 'payment_pending.html', context)


@login_required
def payment_success(request, payment_id):
    """Show payment success page - ONLY if payment is actually successful"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)

    # Only show success page for actually successful payments
    if payment.status != 'successful':
        # If payment is pending, redirect to pending page
        if payment.status == 'pending':
            messages.info(
                request, "Payment is still processing. Please wait for confirmation.")
            return redirect('payment_pending', payment_id=payment.id)
        else:
            # Payment is failed or other status
            messages.error(
                request, "Payment not confirmed. Please complete the payment.")
            return redirect('process_payment', booking_id=payment.booking.id)

    # Only reach here if payment is successful
    context = {
        'payment': payment,
        'booking': payment.booking,
    }
    return render(request, 'payment_successful.html', context)


@login_required
def payment_failed(request, payment_id):
    """Show payment failed page"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)

    context = {
        'payment': payment,
    }
    return render(request, 'payment_failed.html', context)

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
                payment = Payment.objects.get(
                    checkout_request_id=checkout_request_id)
                payment.callback_received = True
                payment.result_code = result_code
                payment.result_desc = result_desc
                payment.callback_data = data

                if result_code == 0:
                    # Payment successful
                    payment.status = 'successful'

                    # Extract M-Pesa receipt number
                    callback_items = callback_metadata.get(
                        'CallbackMetadata', {}).get('Item', [])
                    for item in callback_items:
                        if item.get('Name') == 'MpesaReceiptNumber':
                            payment.mpesa_receipt_number = item.get('Value')
                        elif item.get('Name') == 'TransactionDate':
                            transaction_date = item.get('Value')
                            # Convert M-Pesa date format to datetime
                            try:
                                payment.transaction_date = timezone.make_aware(
                                    datetime.strptime(
                                        str(transaction_date), '%Y%m%d%H%M%S')
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
                print(
                    f"Payment not found for checkout request: {checkout_request_id}")

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
