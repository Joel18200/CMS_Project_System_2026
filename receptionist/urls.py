from django.urls import path
from .views import PatientListCreateAPIView, PatientDetailUpdateAPIView

urlpatterns = [
    # List all patients and register a new patient
    path(
        "patients/",
        PatientListCreateAPIView.as_view(),
        name="patient-list-create",
    ),

    # View or update one patient using their ID
    path(
        "patients/<int:pk>/",
        PatientDetailUpdateAPIView.as_view(),
        name="patient-detail-update",
    ),
]

