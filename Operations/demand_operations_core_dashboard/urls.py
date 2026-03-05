from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path(
        "",
        views.admin_operational_dashboard,
        name="admin_operational_dashboard",
    ),
    path(
        "team-member/<int:member_id>/",
        views.team_member_detail,
        name="team_member_detail",
    ),
]
