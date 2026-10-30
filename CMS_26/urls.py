
from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),

    # Receptionist APIs
    path("api/", include("receptionist.urls")),

    # Lab Technician APIs
    path("lab/", include("labtechnician.urls")),

    # Token authentication
    path("api-token-auth/", obtain_auth_token, name="api_token_auth"),

    # Django REST Framework login
    path("api-auth/", include("rest_framework.urls")),
]
