import json

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F
from django.db.models.functions import TruncDate
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from demand_operations_core.models import (
    OperationalTeam,
    OperationalVisit,
    OperationalVisitStatusLog,
    FollowUP,
)

from demand_operations_core.services.farmer_api import get_farmer_details


@login_required(login_url="/accounts/login/")
def admin_operational_dashboard(request):
    # 1) Date filters from GET
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    visits = OperationalVisit.objects.select_related("assigned_to", "activity")

    if start_date:
        visits = visits.filter(created_at__date__gte=start_date)
    if end_date:
        visits = visits.filter(created_at__date__lte=end_date)

    # 2) Top cards
    total_visits_today = visits.count()
    assigned_visits = visits.filter(assigned_to__isnull=False).count()
    pending_field_visits = visits.filter(assigned_to__isnull=True).count()
    total_bookings_today = visits.filter(status="booked").count()

    # 3) Team performance (Team Performance Metrics table)
    team_qs = visits.values(
        "assigned_to__id",
        "assigned_to__team_member_name",
    ).annotate(
        assigned_count=Count("id"),
        interaction_count=Count(
            "id",
            filter=Q(status__in=[
                "pending-contact",
                "unreachable",
                "visit_confirmed",
                "call_back",
                "rescheduled",
                "rejected",
                "booked",
            ])
        ),
        booked_count=Count("id", filter=Q(status="booked")),
    ).order_by("-assigned_count")

    team_data = [
        {
            "id": row["assigned_to__id"],
            "team_member_name": row["assigned_to__team_member_name"],
            "assigned_count": row["assigned_count"],
            "interaction_count": row["interaction_count"],
            "booked_count": row["booked_count"],
        }
        for row in team_qs
        if row["assigned_to__id"] is not None
    ]

    # 4) Status distribution chart (pie)
    status_qs = visits.values("status").annotate(count=Count("id")).order_by()
    chart_labels = [row["status"] for row in status_qs]
    chart_data = [row["count"] for row in status_qs]

    # 5) Trend chart (per day count)
    trend_qs = (
        visits
        .extra(select={"day": "date(created_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    trend_labels = [row["day"].strftime("%Y-%m-%d") for row in trend_qs]
    trend_data = [row["count"] for row in trend_qs]

    context = {
        "start_date": start_date or "",
        "end_date": end_date or "",
        "total_visits_today": total_visits_today,
        "assigned_visits": assigned_visits,
        "pending_field_visits": pending_field_visits,
        "total_bookings_today": total_bookings_today,
        "team_data": team_data,
        "chart_labels": json.dumps(chart_labels),
        "chart_data": json.dumps(chart_data),
        "trend_labels": json.dumps(trend_labels),
        "trend_data": json.dumps(trend_data),
    }
    return render(
        request,
        "demand_operations_core_dashboard/dashboard.html",
        context,
    )

@login_required(login_url="/accounts/login/")
def team_member_detail(request, member_id):
    member = get_object_or_404(OperationalTeam, id=member_id)
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    visits_query = OperationalVisit.objects.filter(assigned_to=member)

    if start_date and end_date:
        visits_query = visits_query.filter(
            updated_at__date__range=[start_date, end_date]
        )

    booked_count = visits_query.filter(status="booked").count()

    visits = (
        visits_query.order_by("-updated_at")
        .prefetch_related(
            "history",
            "history__media_files",
        )
        .select_related("activity")
        .annotate(
        farmer_id_display=F("activity__farmer_id"),
        plot_id_display=F("activity__plot_id"),
        activity_text=F("activity__activity"),

            # farmer_id_display=F("activity__farmer_id"),
            # #farmer_name=F("activity__farmer__farmer_name"),
            # #plot_id=F("activity__plot__id"),
            # crop_name=F("activity__plot__crop"),
            # variety_name=F("activity__plot__variety"),
            # #plot_area=F("activity__plot__plot_area"),
            # activity_name=F("activity__activity"),
        )
    )
    farmer_info = {}
    for v in visits:
        fid = v.farmer_id_display
        if fid and fid not in farmer_info:
            try:
                farmer_info[fid] = get_farmer_details(fid)
            except Exception:
                farmer_info[fid] = None


    context = {
        "member": member,
        "visits": visits,
        "booked_count": booked_count,
        "start_date": start_date,
        "end_date": end_date,
        "farmer_info": farmer_info,
    }

    return render(
        request,
        "demand_operations_core_dashboard/team_detail.html",
        context,
    )



from django.shortcuts import render
from django.db.models import Count, Q
from django.utils import timezone

from demand_operations_core.models import OperationalVisit  # import path ko match karna

