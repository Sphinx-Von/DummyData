from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from emails.views import trigger_email
from rest_framework.authtoken.views import obtain_auth_token


def root_redirect(request):
    # always start at login page
    return redirect("accounts:login")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),  # login app
    path("dashboard/", include("demand_operations_core_dashboard.urls")),
    path("demand/", include("demand_operations_core.urls")),
    path('api/', include('demand_operations_core.urls')),
    path("", root_redirect, name="root"),    
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),    # opening site -> login page
    path("", include("emails.urls")),
    path("chat/", include("chatapp.urls")),
]

