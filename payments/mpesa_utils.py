import requests
import base64
from datetime import datetime
import json
from django.conf import settings
from django.utils import timezone


class MpesaGateway:
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.callback_url = settings.MPESA_CALLBACK_URL
        self.access_token = None
        self.token_expiry = None

    def get_access_token(self):
        if self.access_token and self.token_expiry and self.token_expiry > timezone.now():
            return self.access_token

        url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        auth_string = f"{self.consumer_key}:{self.consumer_secret}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        headers = {'Authorization': f'Basic {encoded_auth}'}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            self.access_token = data.get('access_token')
            self.token_expiry = timezone.now() + timezone.timedelta(minutes=55)
            return self.access_token
        except requests.exceptions.RequestException as e:
            print(f"Error getting access token: {e}")
            self.access_token = None
            return None

    def generate_password(self, timestamp):
        """Generate M-Pesa API password"""
        data = f"{self.shortcode}{self.passkey}{timestamp}"
        encoded = base64.b64encode(data.encode()).decode()
        return encoded

    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """Initiate STK Push request"""
        access_token = self.get_access_token()
        if not access_token:
            return None, "Failed to get access token"

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = self.generate_password(timestamp)

        url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": self.callback_url,
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc
        }

        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data, None
        except requests.exceptions.RequestException as e:
            print(f"Error in STK Push: {e}")
            return None, str(e)

    def check_transaction_status(self, checkout_request_id):
        """Check M-Pesa transaction status - IMPROVED VERSION"""
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
            response = requests.post(
                url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Debug logging
            print(f"M-Pesa Status Response: {data}")

            # Check for actual result code
            if 'ResultCode' in data:
                result_code = data['ResultCode']
                result_desc = data.get('ResultDesc', '')

                if result_code == 0:
                    # Payment successful
                    return {'status': 'successful', 'message': result_desc, 'data': data}, None
                else:
                    # Payment failed or cancelled
                    return {'status': 'failed', 'message': result_desc, 'data': data}, None
            else:
                # No result code yet - still processing
                return {'status': 'pending', 'message': 'Transaction still processing', 'data': data}, None

        except requests.exceptions.RequestException as e:
            print(f"Error checking transaction: {e}")
            return None, str(e)
