# Operations/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Operations.settings")

app = Celery("Operations")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

