# yourapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("trigger_email/", views.trigger_email, name="trigger_email"),
    path("schedule_email/", views.schedule_email_view, name="schedule_email"),
]
