from django.urls import path
from . import views

urlpatterns = [
    path('process/<int:booking_id>/', views.process_payment, name='process_payment'),
    path('success/<int:payment_id>/', views.payment_success, name='payment_success'),
    path('failed/<int:payment_id>/', views.payment_failed, name='payment_failed'),
    path('pending/<int:payment_id>/', views.payment_pending, name='payment_pending'),
    path('callback/', views.mpesa_callback, name='mpesa_callback'),
]