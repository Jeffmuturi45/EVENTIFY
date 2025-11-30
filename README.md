# EVENTIFY - Event Booking System

A Django-based event booking system with M-Pesa integration.

## Features
- User authentication
- Event management
- Ticket booking
- M-Pesa STK Push payments

## Setup

1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate virtual environment: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and configure your settings
6. Run migrations: `python manage.py migrate`
7. Create superuser: `python manage.py createsuperuser`
8. Run server: `python manage.py runserver`

## Environment Variables

Copy `.env.example` to `.env` and set:
- `SECRET_KEY`: Django secret key
- `DEBUG`: True/False
- `ALLOWED_HOSTS`: comma-separated hosts
- M-Pesa Daraja API credentials

## M-Pesa Setup

1. Get credentials from [Safaricom Daraja](https://developer.safaricom.co.ke/)
2. Update `.env` with your credentials
3. For production, set up proper callback URLs
