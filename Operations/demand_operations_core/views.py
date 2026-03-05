from django.shortcuts import render
from django.http.response import JsonResponse
import json
from demand_operations_core.models import *
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

# Create your views here.

from django.shortcuts import render
from django.db.models import Count, Q
from django.utils import timezone

from .models import FollowUP  # or FollowUp, match your model name exactly

from .models import FollowUP
from django.utils import timezone
from django.db.models import Count, Q

from django.contrib.auth import get_user_model

from .services.farmer_api import get_farmer_details



User = get_user_model()


from django.shortcuts import render, get_object_or_404
from .models import FollowUP
from .services.farmer_api import get_farmer_details

def followup_detail(request, pk):
    followup = get_object_or_404(FollowUP, pk=pk)
    farmer = get_farmer_details(followup.farmer_id)  # returns the JSON you showed[file:1]

    return render(
        request,
        "admin/followup_detail.html",
        {
            "followup": followup,
            "farmer": farmer,
        },
    )




from django.contrib.auth.decorators import login_required


@login_required(login_url='accounts:login')
def followup_dashboard(request):
    # base queryset
    qs = FollowUP.objects.select_related("assigned_to", "created_by")

    # --- filters from GET ---
    status_param = request.GET.get("status")
    if status_param:
        status_map = {
            "pending": FollowUP.Status.PENDING,
            "in_progress": FollowUP.Status.IN_PROGRESS,
            "completed": FollowUP.Status.COMPLETED,
            "cancelled": FollowUP.Status.CANCELLED,
        }
        db_status = status_map.get(status_param)
        if db_status:
            qs = qs.filter(status=db_status)

    priority_param = request.GET.get("priority")
    if priority_param:
        priority_map = {
            "urgent": FollowUP.Priority.URGENT,
            "high": FollowUP.Priority.HIGH,
            "medium": FollowUP.Priority.MEDIUM,
            "low": FollowUP.Priority.LOW,
        }
        db_priority = priority_map.get(priority_param)
        if db_priority:
            qs = qs.filter(priority=db_priority)

    assigned_to_param = request.GET.get("assigned_to")
    if assigned_to_param:
        qs = qs.filter(assigned_to_id=assigned_to_param)

    followup_type_param = request.GET.get("followup_type")
    if followup_type_param:
        qs = qs.filter(followup_type=followup_type_param)

    # --- stats based on *filtered* qs ---
    urgent_count = qs.filter(priority=FollowUP.Priority.URGENT).count()
    high_priority_count = qs.filter(priority=FollowUP.Priority.HIGH).count()
    pending_count = qs.filter(status=FollowUP.Status.PENDING).count()
    completed_count = qs.filter(status=FollowUP.Status.COMPLETED).count()

    # agar purane dashboard stats bhi chahiye to:
    total_followups = qs.count()
    unassigned = qs.filter(assigned_to__isnull=True).count()
    overdue = qs.filter(
        scheduled_date__lt=timezone.now(),
        status__in=[FollowUP.Status.PENDING, FollowUP.Status.IN_PROGRESS],
    ).count()

    by_user = qs.filter(
        assigned_to__isnull=False
    ).values(
        "assigned_to__username",
        "assigned_to__first_name",
        "assigned_to__last_name",
    ).annotate(
        total=Count("id"),
        pending=Count("id", filter=Q(status=FollowUP.Status.PENDING)),
        in_progress=Count("id", filter=Q(status=FollowUP.Status.IN_PROGRESS)),
        completed=Count("id", filter=Q(status=FollowUP.Status.COMPLETED)),
    ).order_by("-total")

    upcoming = qs.filter(
        scheduled_date__gte=timezone.now(),
        status__in=[FollowUP.Status.PENDING, FollowUP.Status.IN_PROGRESS],
    ).order_by("scheduled_date")[:10]

    followups = list(qs.order_by("-created_at"))

    for f in followups:
        try:
            farmer = get_farmer_details(f.farmer_id)
        except Exception:
            farmer = {}

        f.farmer_name = farmer.get("farmer_name", "")
        f.farmer_phone = farmer.get("phone_number", "")
        f.farmer_district = farmer.get("district", "")

        # choose plot for this row
        if f.plot_id:
            f.plot_display = f.plot_id
        else:
            plots = farmer.get("plots") or []
            f.plot_display = plots[0]["plot_id"] if plots else ""


    context = {
        "title": "Follow-Up Dashboard",
        "total_followups": total_followups,
        "pending": pending_count,          # optional: old var name reuse
        "in_progress": qs.filter(status=FollowUP.Status.IN_PROGRESS).count(),
        "completed": completed_count,
        "unassigned": unassigned,
        "overdue": overdue,
        "by_user": by_user,
        "upcoming": upcoming,
        "urgent_count": urgent_count,
        "high_priority_count": high_priority_count,
        "pending_count": pending_count,
        "completed_count": completed_count,
        "users": User.objects.all(),
        "today": timezone.now().date(),
        "followups": followups,
    }
    return render(request, "admin/followup_dashboard.html", context)


@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def allocate_team_member(request):
    """
    Allocates a Team Member to a FollowUp.
    Accepts JSON: {"follow_up_id": 123, "assigned_phone": "9999999999"}
    """

    # 1. DRF's request.data works for both JSON bodies and Form Data
    follow_up_id = request.data.get("follow_up_id")
    assignee_phone = request.data.get("assigned_phone")

    # 2. Validation: Check if data is missing
    if not follow_up_id:
        return Response(
            {"error":  " 'follow_up_id' is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 3. Fetch Objects (optimized)
    try:
        follow_up = FollowUP.objects.get(id=follow_up_id)
    except FollowUP.DoesNotExist:
        return Response(
            {"error": "Follow Up not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # 4. Create the Visit
    try:
        # Using get_or_create prevents duplicate assignments if hit twice
        ops_visit, created = OperationalVisit.objects.get_or_create(
            activity=follow_up,
        )

        if created and assignee_phone:
            msg = "The Operational Visit Instance has been successfully created"
            team_member = OperationalTeam.objects.filter(team_member_phone_number=assignee_phone).first()
            ops_visit.assigned_to=team_member
            ops_visit.save()
            status_code = status.HTTP_201_CREATED
        elif not assignee_phone:
            msg = "The Allocation for this Operational Visit has been Removed"
            ops_visit.assigned_to=None
            ops_visit.save()
            status_code = status.HTTP_200_OK
        else:
            msg = "This Follow Up is re-assigned to this Team Member"
            team_member = OperationalTeam.objects.filter(team_member_phone_number=assignee_phone).first()
            ops_visit.assigned_to=team_member
            ops_visit.save()
            status_code = status.HTTP_200_OK

        return Response({"success": msg, "id": ops_visit.id}, status=status_code)

    except Exception as e:
        # Log the full traceback internally, don't show raw errors to user
        logger.error(f"Error allocating team member: {str(e)}", exc_info=True)
        return Response(
            {"error": "An internal server error occurred."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

from django.db.models import F
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import OperationalVisit
from .serializers import OperationalVisitSerializer
from django.shortcuts import get_object_or_404
from django.db.models import OuterRef,Subquery

from django.shortcuts import render
from django.db.models import Count, Q
from django.utils import timezone
from .models import OperationalVisit







from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from demand_operations_core.models import OperationalVisit, OperationalTeam
from .models import FollowUP   # your FollowUP model

# views.py




@require_http_methods(["GET", "POST"])
def assign_followup(request, followup_id):
    followup = get_object_or_404(FollowUP, id=followup_id)

    if request.method == "POST":
        team_id = request.POST.get("team_member")
        if team_id:
            team_member = get_object_or_404(OperationalTeam, id=team_id)

            ops_visit, _ = OperationalVisit.objects.get_or_create(activity=followup)
            ops_visit.assigned_to = team_member
            ops_visit.save(update_fields=["assigned_to"])

            followup.ops_assigned_to = team_member
            followup.save(update_fields=["ops_assigned_to"])

        return redirect("followup_dashboard")

    team_members = OperationalTeam.objects.all()
    return render(
        request,
        "demand/assign_followup.html",
        {"followup": followup, "team_members": team_members},
    )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def get_operational_visits_list(request):
    """
    Returns a flattened, optimized list of operational visits.
    """
    try:
        # 1. Base Query
        # You can add .filter() here if you need to filter by logged-in user
        # e.g., .filter(assigned_to__team_member_phone_number=request.user.username)
        operations = OperationalVisit.objects.annotate(
            farmer_name = F('activity__farmer__farmer_name'),
            phone_number = F('activity__farmer__phone_number'),
            activity_name= F('activity__activity'),
            village = F('activity__farmer__location__village'),
            taluka = F('activity__farmer__location__taluka'),
            district = F('activity__farmer__location__district'),
            assignee_name = F('assigned_to__team_member_name'),
            assignee_phone_number = F('assigned_to__team_member_phone_number'),
            follow_type = F('activity__followup_type'),
            followup_scheduled_date = F('activity__scheduled_date'),
            crop = F('activity__plot__crop'),
            variety = F('activity__plot__variety'),
            acre = F('activity__plot__plot_area'),
            priority = F('activity__priority'),
            operation_scheduled_visit_date = F('scheduled_visit_date'),
            operation_scheduled_visit_time = F('scheduled_visit_time'),
        ).values(
            'id',             # <--- Vital: Needed to identify which item to Update
            'status',         # <--- Vital: Needed to show current status (Completed/Pending)
            'farmer_name',
            'phone_number',
            'village',
            'taluka',
            'district',
            'assignee_name',
            'assignee_phone_number',
            'follow_type',
            'followup_scheduled_date',
            'operation_scheduled_visit_date',
            'operation_scheduled_visit_time',
            'crop',
            'variety',
            'acre',
            'priority',
            'remarks'         # Optional: If you want to show existing remarks
        ).order_by('-created_at')

        # 2. Return Response
        # Since .values() returns a QuerySet of Dicts, we convert it to a list
        return Response(list(operations), status=status.HTTP_200_OK)

    except Exception as e:
        # Good practice to log this error
        return Response(
            {"error": "Failed to fetch list", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def assigned_get_operational_visits_list(request):
    try:
        # Define the history subquery only for extra details (Note/Date), not for filtering
        latest_log = OperationalVisitStatusLog.objects.filter(
            visit=OuterRef('pk')
        ).order_by('-timestamp')

        operations = OperationalVisit.objects.filter(
            # FAST FILTER: Directly filter the parent model
            status="pending-contact"
        ).annotate(
            # Simple F lookups
            farmer_name=F('activity__farmer__farmer_name'),
            phone_number=F('activity__farmer__phone_number'),
            activity_name=F('activity__activity'),
            plot_id=F('activity__plot__id'),
            village=F('activity__farmer__location__village'),
            taluka=F('activity__farmer__location__taluka'),
            district=F('activity__farmer__location__district'),
            assignee_name=F('assigned_to__team_member_name'),
            assignee_phone_number=F('assigned_to__team_member_phone_number'),
            follow_type=F('activity__followup_type'),
            crop=F('activity__plot__crop'),
            variety=F('activity__plot__variety'),
            acre=F('activity__plot__plot_area'),
            priority=F('activity__priority'),

            # We still use Subquery for these dynamic details
            note=Subquery(latest_log.values('note')[:1]),
            follow_up_date=Subquery(latest_log.values('followup_date')[:1]),
        ).values(
            'id', 'plot_id', 'activity_name', 'status', # use 'status', not 'latest_status'
            'farmer_name', 'phone_number', 'village', 'taluka', 'district',
            'assignee_name', 'assignee_phone_number', 'follow_type',
            'crop', 'variety', 'acre', 'priority', 'note', 'follow_up_date'
        ).order_by('-created_at')

        return Response(list(operations), status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": "Failed to fetch list", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def booked_get_operational_visits_list(request):
    """
    Returns a flattened, optimized list of operational visits.
    """
    try:
        latest_log = OperationalVisitStatusLog.objects.filter(
            visit=OuterRef('pk')
        ).order_by('-timestamp')

        operations = OperationalVisit.objects.filter(
            status="booked"
        ).annotate(
            farmer_name = F('activity__farmer__farmer_name'),
            phone_number = F('activity__farmer__phone_number'),
            activity_name= F('activity__activity'),
            plot_id=F('activity__plot__id'),
            village = F('activity__farmer__location__village'),
            taluka = F('activity__farmer__location__taluka'),
            district = F('activity__farmer__location__district'),
            assignee_name = F('assigned_to__team_member_name'),
            assignee_phone_number = F('assigned_to__team_member_phone_number'),
            follow_type = F('activity__followup_type'),
            # followup_scheduled_date = F('activity__scheduled_date'),
            crop = F('activity__plot__crop'),
            variety = F('activity__plot__variety'),
            acre = F('activity__plot__plot_area'),
            priority = F('activity__priority'),
            note=Subquery(latest_log.values('note')[:1]),
            follow_up_date=Subquery(latest_log.values('followup_date')[:1]),
        ).values(
            'id',
            'plot_id',
            'activity_name',
            'status',
            'farmer_name',
            'phone_number',
            'village',
            'taluka',
            'district',
            'assignee_name',
            'assignee_phone_number',
            'follow_type',
            'crop',
            'variety',
            'acre',
            'priority',
            'note',
            'follow_up_date'
        ).order_by('-created_at')

        # 2. Return Response
        # Since .values() returns a QuerySet of Dicts, we convert it to a list
        return Response(list(operations), status=status.HTTP_200_OK)

    except Exception as e:
        # Good practice to log this error
        return Response(
            {"error": "Failed to fetch list", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def rejected_get_operational_visits_list(request):
    """
    Returns a flattened, optimized list of operational visits.
    """
    try:
        latest_log = OperationalVisitStatusLog.objects.filter(
            visit=OuterRef('pk')
        ).order_by('-timestamp')

        operations = OperationalVisit.objects.filter(
            status="rejected"
        ).annotate(
            farmer_name = F('activity__farmer__farmer_name'),
            phone_number = F('activity__farmer__phone_number'),
            activity_name= F('activity__activity'),
            plot_id=F('activity__plot__id'),
            village = F('activity__farmer__location__village'),
            taluka = F('activity__farmer__location__taluka'),
            district = F('activity__farmer__location__district'),
            assignee_name = F('assigned_to__team_member_name'),
            assignee_phone_number = F('assigned_to__team_member_phone_number'),
            follow_type = F('activity__followup_type'),
            # followup_scheduled_date = F('activity__scheduled_date'),
            crop = F('activity__plot__crop'),
            variety = F('activity__plot__variety'),
            acre = F('activity__plot__plot_area'),
            priority = F('activity__priority'),
            note=Subquery(latest_log.values('note')[:1]),
            follow_up_date=Subquery(latest_log.values('followup_date')[:1]),
        ).values(
            'id',
            'plot_id',
            'activity_name',
            'status',
            'farmer_name',
            'phone_number',
            'village',
            'taluka',
            'district',
            'assignee_name',
            'assignee_phone_number',
            'follow_type',
            'crop',
            'variety',
            'acre',
            'priority',
            'note',
            'follow_up_date'
        ).order_by('-created_at')

        # 2. Return Response
        # Since .values() returns a QuerySet of Dicts, we convert it to a list
        return Response(list(operations), status=status.HTTP_200_OK)

    except Exception as e:
        # Good practice to log this error
        return Response(
            {"error": "Failed to fetch list", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def remainder_get_operational_visits_list(request):
    """
    Returns a flattened, optimized list of operational visits.
    """
    try:
        latest_log = OperationalVisitStatusLog.objects.filter(
            visit=OuterRef('pk')
        ).order_by('-timestamp')

        operations = OperationalVisit.objects.filter(
            status__in=[
                "call_back",
                "rescheduled",
                "unreachable"
                ]
        ).annotate(
            farmer_name = F('activity__farmer__farmer_name'),
            phone_number = F('activity__farmer__phone_number'),
            activity_name= F('activity__activity'),
            plot_id=F('activity__plot__id'),
            village = F('activity__farmer__location__village'),
            taluka = F('activity__farmer__location__taluka'),
            district = F('activity__farmer__location__district'),
            assignee_name = F('assigned_to__team_member_name'),
            assignee_phone_number = F('assigned_to__team_member_phone_number'),
            follow_type = F('activity__followup_type'),
            # followup_scheduled_date = F('activity__scheduled_date'),
            crop = F('activity__plot__crop'),
            variety = F('activity__plot__variety'),
            acre = F('activity__plot__plot_area'),
            priority = F('activity__priority'),
            note=Subquery(latest_log.values('note')[:1]),
            follow_up_date=Subquery(latest_log.values('followup_date')[:1]),
        ).values(
            'id',
            'plot_id',
            'activity_name',
            'status',
            'farmer_name',
            'phone_number',
            'village',
            'taluka',
            'district',
            'assignee_name',
            'assignee_phone_number',
            'follow_type',
            'crop',
            'variety',
            'acre',
            'priority',
            'note',
            'follow_up_date'
        ).order_by('-created_at')

        # 2. Return Response
        # Since .values() returns a QuerySet of Dicts, we convert it to a list
        return Response(list(operations), status=status.HTTP_200_OK)

    except Exception as e:
        # Good practice to log this error
        return Response(
            {"error": "Failed to fetch list", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def confirmed_get_operational_visits_list(request):
    """
    Returns a flattened, optimized list of operational visits.
    """
    try:
        latest_log = OperationalVisitStatusLog.objects.filter(
            visit=OuterRef('pk')
        ).order_by('-timestamp')

        operations = OperationalVisit.objects.filter(
            status="visit_confirmed"
        ).annotate(
            farmer_name = F('activity__farmer__farmer_name'),
            phone_number = F('activity__farmer__phone_number'),
            activity_name= F('activity__activity'),
            plot_id=F('activity__plot__id'),
            village = F('activity__farmer__location__village'),
            taluka = F('activity__farmer__location__taluka'),
            district = F('activity__farmer__location__district'),
            assignee_name = F('assigned_to__team_member_name'),
            assignee_phone_number = F('assigned_to__team_member_phone_number'),
            follow_type = F('activity__followup_type'),
            # followup_scheduled_date = F('activity__scheduled_date'),
            crop = F('activity__plot__crop'),
            variety = F('activity__plot__variety'),
            acre = F('activity__plot__plot_area'),
            priority = F('activity__priority'),
            note=Subquery(latest_log.values('note')[:1]),
            follow_up_date=Subquery(latest_log.values('followup_date')[:1]),
        ).values(
            'id',
            'plot_id',
            'activity_name',
            'status',
            'farmer_name',
            'phone_number',
            'village',
            'taluka',
            'district',
            'assignee_name',
            'assignee_phone_number',
            'follow_type',
            'crop',
            'variety',
            'acre',
            'priority',
            'note',
            'follow_up_date'
        ).order_by('-created_at')

        # 2. Return Response
        # Since .values() returns a QuerySet of Dicts, we convert it to a list
        return Response(list(operations), status=status.HTTP_200_OK)

    except Exception as e:
        # Good practice to log this error
        return Response(
            {"error": "Failed to fetch list", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

from django.utils import timezone

@api_view(['PATCH'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def update_operational_visit(request, pk):
    """
    Updates an Operational Visit.
    Special Logic: If 'status' changes, it triggers the custom update_status() method.

    Payload Example:
    {
        "status": "rescheduled",
        "note": "Farmer is busy, called to call back later",
        "scheduled_visit_date": "2024-12-25",
        "scheduled_visit_time": "10:00:00"
    }
    """
    try:
        visit = get_object_or_404(OperationalVisit, pk=pk)

        data = request.data
        new_status = data.get('status')
        note = data.get('note', "")
        user_number = data.get('user_number',"")

        user = None
        if user_number:
            user = OperationalTeam.objects.filter(team_member_phone_number=user_number).first()


        # 1. Handle Status Change Logic (using your custom method)
        if new_status and new_status != visit.status:
            # Validate that the status is a valid choice
            valid_statuses = [choice[0] for choice in OperationalVisit.STATUS_CHOICES]
            if new_status not in valid_statuses:
                return Response(
                    {"error": f"Invalid status. Choices are: {valid_statuses}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            followup_date = data.get('scheduled_visit_date','')

            # Call your model's custom method to save status AND create log
            visit.update_status(
                new_status=new_status,
                note=note,
                followup_date=followup_date,
                user=user
            )

            return Response({
                "success": "Visit updated successfully",
            }, status=status.HTTP_200_OK)

        else:
            if not new_status:
                return Response({
                    "success":"Visit details updated (No status provided)"
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "success":"Visit Status Updated (Status Unchanged)"
                }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import OperationalTeam
from .serializers import OperationalTeamSerializer

@api_view(['POST'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def create_operational_member(request):
    # Extract phone number from the request data
    member_name = request.data.get("team_member_name")
    phone_number = request.data.get('team_member_phone_number')

    if not phone_number:
        return Response(
            {"error": "Phone number is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # CHECK: Does this phone number already exist?
    existing_member = OperationalTeam.objects.filter(team_member_phone_number=phone_number).first()

    if existing_member:
        # If exists, return success message (Idempotent approach)
        return Response(
            {
                "message": "Member already exists with this phone number.",
                "data": {
                    "id": existing_member.id,
                    "name": existing_member.team_member_name
                }
            },
            status=status.HTTP_200_OK
        )

    elif not existing_member:
        return Response(
            {
                "message": "Member were not in the DB, Please ask for the admin",
            },
            status=status.HTTP_200_OK
        )

    # CREATE: If not exists, pass data to serializer
    # serializer = OperationalTeamSerializer(data=request.data)

    # if serializer.is_valid():
    #     serializer.save()
    #     return Response(
    #         {
    #             "message": "Member created successfully",
    #             "data": serializer.data
    #         },
    #         status=status.HTTP_201_CREATED
    #     )

    # # Return validation errors if data is invalid
    # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
import logging

from .models import (
    OperationalVisitMedia,
    OperationalVisit,
    OperationalVisitStatusLog,
    OperationalTeam,
)
from .serializers import OperationalVisitMediaSerializer

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_operational_visit_media(request):
    """
    Create media for an operational visit with optional location data.
    Auto-creates status log if it doesn't exist.
    Optionally creates OperationalMediaLocation if GPS coordinates are provided.
    """
    try:
        # ============= VALIDATION & DATA EXTRACTION =============
        user_number = request.data.get('user_number', '').strip()
        status_type = request.data.get('status', '').strip()
        operation_visit_pk = request.data.get('operation_visit_pk')
        s3_key = request.data.get('image', '').strip()
        media_type = request.data.get('media_type', 'image').lower().strip()
        caption = request.data.get('caption', '').strip()

        # Location fields (optional)
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        altitude = request.data.get('altitude')
        accuracy = request.data.get('accuracy')
        address = request.data.get('address', '').strip()

        logger.info("Inside the Create operation Function")

        # Validate required fields
        errors = {}
        if not user_number:
            errors['user_number'] = 'User number is required.'
        if not status_type:
            errors['status'] = 'Status is required.'
        if not operation_visit_pk:
            errors['operation_visit_pk'] = 'Operation visit ID is required.'
        if not s3_key:
            errors['image'] = 'S3 key (image) is required.'

        if errors:
            return Response(
                {'success': False, 'message': 'Validation failed', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate media_type
        valid_media_types = ['image', 'video']
        if media_type not in valid_media_types:
            return Response(
                {
                    'success': False,
                    'message': f'Invalid media type. Must be one of {valid_media_types}.',
                    'errors': {'media_type': f'Invalid choice. Expected one of {valid_media_types}.'},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ============= LOCATION VALIDATION =============
        # Check if location data is provided (both latitude and longitude are required for location)
        has_location_data = latitude is not None and longitude is not None

        if has_location_data:
            location_errors = {}

            # Validate latitude and longitude
            try:
                latitude = float(latitude)
                if not -90 <= latitude <= 90:
                    location_errors['latitude'] = 'Latitude must be between -90 and 90.'
            except (ValueError, TypeError):
                location_errors['latitude'] = 'Latitude must be a valid decimal number.'

            try:
                longitude = float(longitude)
                if not -180 <= longitude <= 180:
                    location_errors['longitude'] = 'Longitude must be between -180 and 180.'
            except (ValueError, TypeError):
                location_errors['longitude'] = 'Longitude must be a valid decimal number.'

            # Validate optional altitude and accuracy
            if altitude is not None:
                try:
                    altitude = float(altitude)
                except (ValueError, TypeError):
                    location_errors['altitude'] = 'Altitude must be a valid number.'

            if accuracy is not None:
                try:
                    accuracy = float(accuracy)
                    if accuracy < 0:
                        location_errors['accuracy'] = 'Accuracy must be a non-negative number.'
                except (ValueError, TypeError):
                    location_errors['accuracy'] = 'Accuracy must be a valid number.'

            if location_errors:
                return Response(
                    {
                        'success': False,
                        'message': 'Location validation failed',
                        'errors': location_errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ============= DATABASE LOOKUPS =============

        # 1. Get OperationalTeam by phone number
        operational_team = OperationalTeam.objects.filter(
            team_member_phone_number=user_number
        ).first()

        if not operational_team:
            logger.warning(f'OperationalTeam not found for phone: {user_number}')
            return Response(
                {
                    'success': False,
                    'message': f'Team member with phone number {user_number} not found.',
                    'errors': {'user_number': 'No team member found with this phone number.'},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2. Get OperationalVisit by pk
        operational_visit = OperationalVisit.objects.filter(pk=operation_visit_pk).first()

        if not operational_visit:
            logger.warning(f'OperationalVisit not found with pk: {operation_visit_pk}')
            return Response(
                {
                    'success': False,
                    'message': f'Operation visit with ID {operation_visit_pk} not found.',
                    'errors': {'operation_visit_pk': 'No operation visit found with this ID.'},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # 3. Get or CREATE OperationalVisitStatusLog
        try:
            # Try to get the most recent status log
            visit_status_log = OperationalVisitStatusLog.objects.filter(
                visit=operational_visit,
                status=status_type,
            ).order_by("-timestamp").first()

            created = False

            # If no status log exists, create one
            if visit_status_log is None:
                visit_status_log = OperationalVisitStatusLog.objects.create(
                    visit=operational_visit,
                    status=status_type,
                    created_by=operational_team,
                    note='Auto-created for media upload',
                    timestamp=timezone.now(),
                )
                created = True
                logger.info(
                    f'Auto-created StatusLog: visit={operation_visit_pk}, '
                    f'status={status_type}, created_by={operational_team.id}'
                )
            else:
                logger.info(
                    f'Using existing StatusLog: visit={operation_visit_pk}, '
                    f'status={status_type}, timestamp={visit_status_log.timestamp}'
                )

        except Exception as e:
            logger.error(f'Error creating/fetching StatusLog: {e}')
            return Response(
                {
                    'success': False,
                    'message': 'Failed to process visit status.',
                    'errors': {'status': str(e)},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ============= CREATE MEDIA OBJECT =============

        media_object = OperationalVisitMedia(
            visit=visit_status_log,
            file=s3_key,
            media_type=media_type,
            caption=caption,
            uploaded_by=operational_team,
        )

        try:
            media_object.full_clean()
            media_object.save()
            logger.info(
                f'Media created: ID={media_object.id}, Visit={operation_visit_pk}, '
                f'Type={media_type}, UploadedBy={operational_team.id}'
            )

            # ============= CREATE LOCATION OBJECT (IF DATA PROVIDED) =============
            location_object = None
            if has_location_data:
                try:
                    location_object = OperationalMediaLocation.objects.create(
                        media=media_object,
                        latitude=latitude,
                        longitude=longitude,
                        altitude=altitude,
                        accuracy=accuracy,
                        address=address if address else None,
                    )
                    logger.info(
                        f'Location created: ID={location_object.id}, Media={media_object.id}, '
                        f'Coords=({latitude}, {longitude})'
                    )
                except Exception as location_error:
                    # Log the error but don't fail the entire request
                    # Media was created successfully, location creation failed
                    logger.error(
                        f'Failed to create location for media {media_object.id}: {location_error}'
                    )
                    return Response(
                        {
                            'success': False,
                            'message': 'Media uploaded but location data could not be saved.',
                            'errors': {'location': str(location_error)},
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # ============= SUCCESS RESPONSE =============
            response_data = {
                'success': True,
                'message': 'Media uploaded successfully.',
                'data': {
                    'media_id': media_object.id,
                    'media_type': media_object.media_type,
                    'created_at': media_object.created_at.isoformat(),
                },
            }

            # Add location data to response if it was created
            if location_object:
                response_data['data']['location'] = {
                    'location_id': location_object.id,
                    'latitude': str(location_object.latitude),
                    'longitude': str(location_object.longitude),
                    'altitude': location_object.altitude,
                    'accuracy': location_object.accuracy,
                    'address': location_object.address,
                    'created_at': location_object.created_at.isoformat(),
                }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as validation_error:
            logger.error(f'Model validation failed: {validation_error}')
            return Response(
                {
                    'success': False,
                    'message': 'Media object validation failed.',
                    'errors': {'detail': str(validation_error)},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        logger.exception('Unexpected error in create_operational_visit_media')
        return Response(
            {
                'success': False,
                'message': 'An unexpected error occurred.',
                'errors': {'detail': 'Internal server error'},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


from rest_framework import status
from django.core.exceptions import ValidationError

@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def get_operational_history(request, pk):
    try:
        # Get single operation or return 404
        try:
            ops = OperationalVisit.objects.get(id=pk)
        except OperationalVisit.DoesNotExist:
            return Response(
                {"message": "Operation Not Found, Please Check the ID"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get logs for this specific operation
        logs = OperationalVisitStatusLog.objects.filter(
            visit=ops  # Now ops is a single object, not a QuerySet
        ).order_by(
            "-timestamp"
        ).values(
            "status",
            "timestamp",
            "note",
            "followup_date"
        )

        # Return the logs
        return Response({
            "operation_id": pk,
            "logs": list(logs)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def create_followup(request):
    data = request.data

    # 1. Extract IDs
    farmer_id = data.get('farmer_id')
    plot_id = data.get('plot_id')
    ops_member_number = data.get('user_number')
    remarks = data.get('remarks','-')

    ops_member = OperationalTeam.objects.filter(
        team_member_phone_number=ops_member_number
    ).first()

    if not ops_member:
        return Response({
            "error":"No Team Member has been found on this Number"
        },status=status.HTTP_200_OK)

    if not farmer_id:
        return Response(
            {"error": "farmer_id is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 2. Get Farmer (Safe lookup)
    farmer = get_object_or_404(Farmer, farmer_id=farmer_id)

    # 3. Get Plot (Validate ownership)
    # We ensure the plot actually belongs to this farmer for safety
    plot = None
    if plot_id:
        # Assuming Plot has a ForeignKey to Farmer named 'farmer'
        plot = get_object_or_404(Plot, id=plot_id, farmer=farmer)

    try:
        # 4. Create Instance
        # We use .get() for optional fields to avoid KeyErrors
        followup = FollowUP.objects.create(
            farmer=farmer,
            plot=plot,
            followup_type=data.get('followup_type', FollowUP.FollowUpType.CALL_BACK),
            activity=data.get('activity'),
            scheduled_date=data.get('scheduled_date'), # e.g., "2023-12-25T10:00:00Z"
            notes=data.get('notes'),
            priority=data.get('priority', 'MEDIUM'),
            created_by=request.user  # Auto-assign the logged-in user
        )

        opv = OperationalVisit.objects.create(
            activity = followup,
            assigned_to = ops_member,
            remarks = remarks,
        )

        opv.update_status(new_status=opv.status,user=ops_member)

        return Response({
            "id": followup.id,
            "message": "Follow-up created successfully.",
            "status": "success"
        }, status=status.HTTP_201_CREATED)

    except ValidationError as e:
        # Handles model-level validation errors (e.g. invalid date format)
        return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # Fallback for other unexpected errors
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)






# API for Followup Bulk Create

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import FollowUP
from .serializers import FollowupBulkCreateSerializer, FollowUPSerializer

class FollowupBulkCreateAPIView(APIView):
    # permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        serializer = FollowupBulkCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        followups = serializer.save()
        out = FollowUPSerializer(followups, many=True)
        return Response(out.data, status=status.HTTP_201_CREATED)
