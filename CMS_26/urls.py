
from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("receptionist.urls")),
    path("api/", include("labtechnician.urls")),
    path("api/", include("doctor.urls")),
    path("api/", include("pharmacist.urls")),
]
