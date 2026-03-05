# yourapp/views.py
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from .forms import ScheduleEmailForm
from .tasks import send_simple_email


def trigger_email(request):
    """
    Trigger immediate email via Celery.
    """
    message = (
        "Life’s too short to be serious all the time! "
        "Dance like no one’s got video evidence, "
        "Laugh until your stomach complains, "
        "And remember — naps count as self-care, not laziness. "
        "Stay weird, stay wonderful! "
        "Hi Samruddhi, Tanushri I tried Celery today so just checking if it's working or not."
    )

    send_simple_email.delay(
        subject="Hello from Celery",
        message=message,
        recipient=[
            "rubinahakim95@gmail.com",
            "2022bcs037@sggs.ac.in",
            "2022bcs039@sggs.ac.in",
            "2022bcs031@sggs.ac.in",
        ],
    )
    return HttpResponse("Email task queued!")


def schedule_email_view(request):
    """
    Schedule an email for a specific time using Celery's eta.
    """
    if request.method == "POST":
        form = ScheduleEmailForm(request.POST)
        if form.is_valid():
            recipient = [form.cleaned_data["recipient"]]
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]
            send_at = form.cleaned_data["send_at"]

            # Make send_at timezone-aware using Django timezone
            if timezone.is_naive(send_at):
                send_at = timezone.make_aware(
                    send_at, timezone.get_current_timezone()
                )

            send_simple_email.apply_async(
                kwargs={
                    "subject": subject,
                    "message": message,
                    "recipient": recipient,
                },
                eta=send_at,
            )
            return redirect("schedule_email")
    else:
        form = ScheduleEmailForm()

    return render(request, "schedule_email.html", {"form": form})
