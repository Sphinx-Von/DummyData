# yourapp/models.py
from django.db import models

class ScheduledEmail(models.Model):
    to_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    send_at = models.DateTimeField()
    sent = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["send_at", "sent"])]

    def __str__(self):
        return f"{self.to_email} at {self.send_at}"
