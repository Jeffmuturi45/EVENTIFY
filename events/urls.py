from django.urls import path
from . import views
from django.conf.urls.static import static

urlpatterns = [
    path('', views.event_list, name='home'),
    # We'll add more later
]
