from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime
from .mpesa_utils import MpesaGateway

# Payment Model


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    # Relationships
    booking = models.OneToOneField(
        'bookings.Booking', on_delete=models.CASCADE, related_name='payment')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='payments')

    # Payment Details
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # M-Pesa Details
    merchant_request_id = models.CharField(max_length=100, blank=True)
    checkout_request_id = models.CharField(max_length=100, blank=True)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True)
    transaction_date = models.DateTimeField(null=True, blank=True)

    # M-Pesa Callback Details
    callback_received = models.BooleanField(default=False)
    result_code = models.IntegerField(null=True, blank=True)
    result_desc = models.TextField(blank=True)
    callback_data = models.JSONField(
        null=True, blank=True)  # Store full callback data

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment #{self.id} - {self.user.username} - KSh {self.amount}"

    def check_mpesa_status(self):
        """Check actual M-Pesa transaction status - IMPROVED"""
        if not self.checkout_request_id:
            return None, "No checkout request ID"

        if self.status == 'successful' or self.status == 'failed':
            return self.status, "Status already finalized"

        # Import here to avoid circular imports
        from .mpesa_utils import MpesaGateway

        mpesa = MpesaGateway()
        response, error = mpesa.check_transaction_status(
            self.checkout_request_id)

        if error:
            print(f"M-Pesa status check error: {error}")
            return None, error

        if response:
            result_status = response.get('status')
            result_message = response.get('message', '')

            print(f"M-Pesa Status: {result_status}, Message: {result_message}")

            if result_status == 'successful':
                # Payment successful
                self.status = 'successful'

                # Try to extract receipt number from response data
                response_data = response.get('data', {})
                if response_data.get('ResultCode') == 0:
                    # Extract from callback metadata if available
                    callback_metadata = response_data.get(
                        'CallbackMetadata', {})
                    if callback_metadata:
                        items = callback_metadata.get('Item', [])
                        for item in items:
                            if item.get('Name') == 'MpesaReceiptNumber':
                                self.mpesa_receipt_number = item.get(
                                    'Value', f"MPE{self.id:08d}")
                            elif item.get('Name') == 'TransactionDate':
                                transaction_date = item.get('Value')
                                try:
                                    self.transaction_date = timezone.make_aware(
                                        datetime.strptime(
                                            str(transaction_date), '%Y%m%d%H%M%S')
                                    )
                                except:
                                    self.transaction_date = timezone.now()

                # Update booking status
                self.booking.status = 'confirmed'
                self.booking.save()

            elif result_status == 'failed':
                # Payment failed
                self.status = 'failed'

            self.save()
            return self.status, result_message

        return None, "No response from M-Pesa"

    def update_status_from_callback(self, callback_data):
        """Update status from M-Pesa callback"""
        try:
            callback_metadata = callback_data.get(
                'Body', {}).get('stkCallback', {})
            result_code = callback_metadata.get('ResultCode')
            result_desc = callback_metadata.get('ResultDesc')

            self.callback_received = True
            self.result_code = result_code
            self.result_desc = result_desc
            self.callback_data = callback_data

            if result_code == 0:
                # Payment successful
                self.status = 'successful'
                # Extract receipt number
                callback_items = callback_metadata.get(
                    'CallbackMetadata', {}).get('Item', [])
                for item in callback_items:
                    if item.get('Name') == 'MpesaReceiptNumber':
                        self.mpesa_receipt_number = item.get('Value')
                    elif item.get('Name') == 'TransactionDate':
                        transaction_date = item.get('Value')
                        try:
                            self.transaction_date = timezone.make_aware(
                                datetime.strptime(
                                    str(transaction_date), '%Y%m%d%H%M%S')
                            )
                        except:
                            self.transaction_date = timezone.now()

                # Update booking status
                self.booking.status = 'confirmed'
                self.booking.save()
            else:
                # Payment failed or cancelled
                self.status = 'failed'

            self.save()
            return True
        except Exception as e:
            print(f"Error updating from callback: {e}")
            return False

    @property
    def is_successful(self):
        return self.status == 'successful'

    @property
    def formatted_phone(self):
        """Format phone number for M-Pesa"""
        phone = self.phone_number.strip()
        if phone.startswith('0'):
            return '254' + phone[1:]
        elif phone.startswith('+254'):
            return phone[1:]
        elif phone.startswith('254'):
            return phone
        return '254' + phone
