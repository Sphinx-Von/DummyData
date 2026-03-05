from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_simple_email(subject, message, recipient):
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient,
        fail_silently=False,
    )



# yourapp/tasks.py
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from .models import ScheduledEmail

@shared_task
def process_scheduled_emails():
    now = timezone.now()
    emails = ScheduledEmail.objects.filter(sent=False, send_at__lte=now)

    for email in emails:
        send_mail(
            email.subject,
            email.body,
            "rubinahakim95@gmail.com",  # change to your from address
            [email.to_email],
        )
        email.sent = True
        email.save(update_fields=["sent"])
