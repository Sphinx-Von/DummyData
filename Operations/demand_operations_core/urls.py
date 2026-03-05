from django.urls import path
from .views import *
from . import views

urlpatterns = [
    path("allocate_team_member/", allocate_team_member, name="allocate_team_member"),

    path('visits/', get_operational_visits_list, name='get_visits'),

    path('assigned_visits/', assigned_get_operational_visits_list, name='assigned_get_visits'),
    path('conformed_visits/', confirmed_get_operational_visits_list, name='conformed_get_visits'),
    path('booked_visits/', booked_get_operational_visits_list, name='booked_get_visits'),
    path('rejected_visits/', rejected_get_operational_visits_list, name='rejected_get_visits'),
    path('remainder_visits/', remainder_get_operational_visits_list, name='remainder_get_visits'),

    path('visits/<int:pk>/update/', update_operational_visit, name='update_visit'),

    path("get_operations_history/<str:pk>/", get_operational_history, name="get_operational_history"),

    path("create_operational_visit_media/", create_operational_visit_media, name="create_operational_visit_media"),

    path('create_ops_member/', create_operational_member, name='create-operational-member'),

    # Create FollowUP
    path("api/create_followup/", create_followup, name="create_followup"),

    path("followups/bulk-create/", FollowupBulkCreateAPIView.as_view(), name='followups-bulk-create'), #api 

    path(
        "followups/dashboard/",
        views.followup_dashboard,
        name="followup_dashboard",
    ),
    path(
    "followups/<int:followup_id>/assign/",
    views.assign_followup,
    name="assign_followup",
    ),

    path("followups/<int:pk>/", views.followup_detail, name="followup_detail"),

]
