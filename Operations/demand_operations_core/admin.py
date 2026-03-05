from django.contrib import admin
from .models import *
# Register your models here.


# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Q
from django.urls import path
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from .models import FollowUP

@admin.register(FollowUP)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'followup_type_badge',
        'farmer_id',
        'plot_id',
        'priority_badge',
        'status_badge',
        'assigned_to_link',
        'scheduled_date',
        'created_by',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'priority',
        'followup_type',
        'assigned_to',
        'created_by',
        ('scheduled_date', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
    ]
    
    search_fields = [
        'farmer_id',
        'plot_id',
        'activity',
        'notes',
        'assigned_to__username',
        'assigned_to__first_name',
        'assigned_to__last_name',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'assigned_date',
        'completed_date',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'followup_type',
                'farmer_id',
                'plot_id',
                'activity',
            )
        }),
        ('Scheduling & Priority', {
            'fields': (
                'scheduled_date',
                'priority',
                'status',
            )
        }),
        ('Assignment', {
            'fields': (
                'assigned_to',
                'assigned_date',
            ),
            'classes': ('wide',),
        }),
        ('Additional Information', {
            'fields': (
                'notes',
                'completed_date',
            )
        }),
        ('Tracking', {
            'fields': (
                'created_by',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    list_per_page = 25
    
    actions = [
        'assign_to_me',
        'mark_as_in_progress',
        'mark_as_completed',
        'mark_as_pending',
        'set_priority_high',
        'set_priority_urgent',
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('assigned_to', 'created_by')
    
    # Custom display methods
    def followup_type_badge(self, obj):
        colors = {
            'CALLBACK': '#3498db',
            'FIELD_VISIT': '#2ecc71',
            'SEND_INFO': '#f39c12',
            'PARKED': '#95a5a6',
        }
        color = colors.get(obj.followup_type, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_followup_type_display()
        )
    followup_type_badge.short_description = 'Type'
    
    def priority_badge(self, obj):
        colors = {
            'LOW': '#95a5a6',
            'MEDIUM': '#3498db',
            'HIGH': '#f39c12',
            'URGENT': '#e74c3c',
        }
        color = colors.get(obj.priority, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    def status_badge(self, obj):
        colors = {
            'PENDING': '#f39c12',
            'IN_PROGRESS': '#3498db',
            'COMPLETED': '#2ecc71',
            'CANCELLED': '#95a5a6',
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def assigned_to_link(self, obj):
     if obj.assigned_to:
        return format_html(
            '<span style="color: #2ecc71; font-weight: bold;">✓ {}</span>',
            obj.assigned_to.get_full_name() or obj.assigned_to.username,
        )
    # No placeholders -> just return the string directly
     return '<span style="color: #e74c3c;">Unassigned</span>'
    assigned_to_link.short_description = 'Assigned To'
    assigned_to_link.admin_order_field = 'assigned_to'

    # Custom actions
    @admin.action(description='Assign selected follow-ups to me')
    def assign_to_me(self, request, queryset):
        updated = queryset.update(
            assigned_to=request.user,
            assigned_date=timezone.now()
        )
        self.message_user(request, f'{updated} follow-up(s) assigned to you.')
    
    @admin.action(description='Mark as In Progress')
    def mark_as_in_progress(self, request, queryset):
        updated = queryset.update(status=FollowUP.Status.IN_PROGRESS)
        self.message_user(request, f'{updated} follow-up(s) marked as in progress.')
    
    @admin.action(description='Mark as Completed')
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(
            status=FollowUP.Status.COMPLETED,
            completed_date=timezone.now()
        )
        self.message_user(request, f'{updated} follow-up(s) marked as completed.')
    
    @admin.action(description='Mark as Pending')
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status=FollowUP.Status.PENDING)
        self.message_user(request, f'{updated} follow-up(s) marked as pending.')
    
    @admin.action(description='Set priority to HIGH')
    def set_priority_high(self, request, queryset):
        updated = queryset.update(priority=FollowUP.Priority.HIGH)
        self.message_user(request, f'{updated} follow-up(s) priority set to HIGH.')
    
    @admin.action(description='Set priority to URGENT')
    def set_priority_urgent(self, request, queryset):
        updated = queryset.update(priority=FollowUP.Priority.URGENT)
        self.message_user(request, f'{updated} follow-up(s) priority set to URGENT.')
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    # Add custom dashboard view


@admin.register(OperationalTeam)
class OperationalTeamAdmin(admin.ModelAdmin):
    list_display = (
        "team_member_name",
        "team_member_phone_number",
        "team_member_mail",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "team_member_name",
        "team_member_phone_number",
        "team_member_mail",
    )


@admin.register(OperationalVisit)
class OperationalVisitAdmin(admin.ModelAdmin):
    list_display = (
        "activity",
        "assigned_to",
        "status",
        "scheduled_visit_date",
        "scheduled_visit_time",
        "remarks",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "activity",
        "assigned_to__team_member_phone_number",
        "assigned_to__team_member_name",
        "status",
        "scheduled_visit_date",
        "scheduled_visit_time",
        "remarks",
    )


@admin.register(OperationalVisitStatusLog)
class OperationalVisitStatusLogAdmin(admin.ModelAdmin):
    list_display = (
        "visit",
        "status",
        "timestamp",
        "followup_date",
        "note",
    )
    search_fields = (
        "visit",
        "status",
        "note",
    )


@admin.register(OperationalVisitMedia)
class OperationalVisitMediaAdmin(admin.ModelAdmin):

    list_display = (
        "farmer_name",
        "visit_status",
        "file",
        "media_type",
        "caption",
        "uploaded_by",
        "created_at",
    )
    search_fields = (
        "file",
        "media_type",
        "caption",
        "uploaded_by__team_member_name",
    )

    def farmer_name(self, obj):
        # Adjust this chain if your relations changed
        visit_log = getattr(obj, "visit", None)
        if visit_log and getattr(visit_log, "visit", None):
            activity = visit_log.visit.activity
            # if activity has only farmer_id now, show that instead
            return getattr(activity, "farmer_name", None) or getattr(activity, "farmer_id", "-")
        return "-"
    farmer_name.short_description = "Farmer"

    def visit_status(self, obj):
        visit_log = getattr(obj, "visit", None)
        if visit_log and getattr(visit_log, "visit", None):
            return visit_log.visit.status
        return "-"
    visit_status.short_description = "Visit status"



@admin.register(OperationalMediaLocation)
class OperationalMediaLocationAdmin(admin.ModelAdmin):
    list_display = (
        "farmer_name",
        "uploaded_by_name",
        "visit_status",
        "latitude",
        "longitude",
        "altitude",
        "accuracy",
        "address",
        "created_at",
    )
    search_fields = (
        "address",
    )

    def farmer_name(self, obj):
        media = getattr(obj, "media", None)
        if media and getattr(media, "visit", None) and getattr(media.visit, "visit", None):
            activity = media.visit.visit.activity
            return getattr(activity, "farmer_name", None) or getattr(activity, "farmer_id", "-")
        return "-"
    farmer_name.short_description = "Farmer"

    def uploaded_by_name(self, obj):
        media = getattr(obj, "media", None)
        if media and media.uploaded_by:
            return media.uploaded_by.team_member_name
        return "-"
    uploaded_by_name.short_description = "Uploaded by"

    def visit_status(self, obj):
        media = getattr(obj, "media", None)
        if media and getattr(media, "visit", None) and getattr(media.visit, "visit", None):
            return media.visit.visit.status
        return "-"
    visit_status.short_description = "Visit status"



