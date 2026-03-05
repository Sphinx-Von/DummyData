from django.db import models

from django.utils import timezone
from django.conf import settings
 

#additional models.py

from django.db import models
import uuid
from django.utils import timezone


# models.py
from django.db import models
from django.conf import settings

class FollowUP(models.Model):
    class FollowUpType(models.TextChoices):
        CALL_BACK = "CALLBACK", "Call Back"
        FIELD_VISIT = "FIELD_VISIT", "Field Visit"
        SEND_INFO = "SEND_INFO", "Send Info"
        PARKED = "PARKED", "Parked"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    followup_type = models.CharField(
        max_length=20,
        choices=FollowUpType.choices,
        default=FollowUpType.CALL_BACK
    )
    
    plot_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="ID of the plot (string or external ID).",
    )
    
    farmer_id = models.CharField(
        max_length=255,
        help_text="ID of the farmer (string or external ID).",
    )
    
    activity = models.TextField(
        null=True,
        blank=True
    )
    
    scheduled_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When should this follow-up be done?"
    )
    
    notes = models.TextField(
        null=True, 
        blank=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    
    # Assignment fields
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assigned_followups',
        null=True,
        blank=True,
        help_text="User assigned to handle this follow-up"
    )

    ops_assigned_to = models.ForeignKey(
        "OperationalTeam",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='followups',
        help_text="Operational team member assigned to this follow-up",
    )
    
    assigned_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was this follow-up assigned?"
    )
    
    completed_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was this follow-up completed?"
    )
    
    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='followups_created',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = "Follow Up"
        verbose_name_plural = "Follow Ups"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'assigned_to']),
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['priority', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_followup_type_display()} - {self.farmer_id} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Auto-set assigned_date when assigned_to is set
        if self.assigned_to and not self.assigned_date:
            from django.utils import timezone
            self.assigned_date = timezone.now()
        
        # Auto-set completed_date when status changes to COMPLETED
        if self.status == self.Status.COMPLETED and not self.completed_date:
            from django.utils import timezone
            self.completed_date = timezone.now()
        
        super().save(*args, **kwargs)


#app models.py

class OperationalTeam(models.Model):
    team_member_name = models.CharField(max_length=150)
    team_member_phone_number = models.CharField(max_length=15)
    team_member_mail = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.team_member_name


class OperationalVisit(models.Model):

    STATUS_CHOICES = (
        ("pending-contact", "Pending Contact"),
        ("unreachable","UnReachable"),
        ("visit_confirmed","Going To Visit"),
        ("call_back","Call Back Again"),
        ("rescheduled", "Visit Rescheduled"),
        ("rejected", "Rejected"),
        ("booked","Booked"),
    )

    activity = models.ForeignKey(FollowUP, on_delete=models.CASCADE, related_name="operations_visit")
    assigned_to = models.ForeignKey(OperationalTeam, on_delete=models.SET_NULL, null=True, blank=True)

    # Current state of the visit
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="pending-contact")

    scheduled_visit_date = models.DateField(null=True, blank=True)
    scheduled_visit_time = models.TimeField(null=True, blank=True)

    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def update_status(self, new_status, note="", followup_date=None,user=None):
        """Helper to update status & log it automatically"""
        self.status = new_status
        self.save()

        OperationalVisitStatusLog.objects.create(
            visit=self,
            status=new_status,
            note=note,
            followup_date=followup_date,
            created_by=user,
        )

    def __str__(self):
        return f"Visit for: {self.activity}"


class OperationalVisitStatusLog(models.Model):
    visit = models.ForeignKey(OperationalVisit, on_delete=models.CASCADE, related_name="history")
    status = models.CharField(max_length=50, choices=OperationalVisit.STATUS_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)

    # Optional: Used when farmer reschedules or asks for callback
    followup_date = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(OperationalTeam, on_delete=models.SET_NULL, null=True, blank=True)

    note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.timestamp} - {self.status}"


class OperationalVisitMedia(models.Model):
    MEDIA_TYPES = (
        ("image", "Image"),
        ("video", "Video"),
    )

    visit = models.ForeignKey(
        OperationalVisitStatusLog,
        on_delete=models.CASCADE,
        related_name="media_files"
    )

    file = models.TextField(blank=True,null=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)

    caption = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        OperationalTeam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.media_type.title()} for Visit #{self.visit.id}"


class OperationalMediaLocation(models.Model):
    media = models.OneToOneField(
        OperationalVisitMedia,
        on_delete=models.CASCADE,
        related_name="location"
    )

    # Core GPS data
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        help_text="Latitude in decimal degrees"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        help_text="Longitude in decimal degrees"
    )

    # Extra metadata from device
    altitude = models.FloatField(
        null=True, blank=True,
        help_text="Altitude in meters"
    )
    accuracy = models.FloatField(
        null=True, blank=True,
        help_text="GPS accuracy in meters"
    )

    # Human readable address (reverse-geocoded)
    address = models.TextField(
        null=True, blank=True,
        help_text="Resolved address at time of capture"
    )

    # Device + capture info
    captured_at = models.DateTimeField(
        null=True, blank=True,
        default=timezone.now,
        help_text="When the media was captured on device"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Media #{self.media.id} @ ({self.latitude}, {self.longitude})"












