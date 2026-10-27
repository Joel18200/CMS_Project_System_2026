
from django.urls import path

from .views import (
    DoctorDailyAppointmentsView,
    DoctorAppointmentDetailView,
    DoctorProfileListView,
    DoctorProfileDetailView,
    DoctorScheduleListView,
    DoctorScheduleDetailView,
    ConsultationListCreateView,
    ConsultationDetailView,
    ClinicalNoteListCreateView,
    ClinicalNoteDetailView,
    PrescriptionListCreateView,
    PrescriptionDetailView,
    PrescriptionItemListCreateView,
    PrescriptionItemDetailView,
    SurgeryAdviceListCreateView,
    SurgeryAdviceDetailView,
)

urlpatterns = [
    path("appointments/", DoctorDailyAppointmentsView.as_view()),
    path(
        "appointments/<int:appointment_id>/",
        DoctorAppointmentDetailView.as_view(),
    ),

    path("profile/", DoctorProfileListView.as_view()),
    path("profile/<int:doctor_id>/", DoctorProfileDetailView.as_view()),

    path("schedules/", DoctorScheduleListView.as_view()),
    path("schedules/<int:pk>/", DoctorScheduleDetailView.as_view()),

    path("consultations/", ConsultationListCreateView.as_view()),
    path("consultations/<int:pk>/", ConsultationDetailView.as_view()),

    path("notes/", ClinicalNoteListCreateView.as_view()),
    path("notes/<int:pk>/", ClinicalNoteDetailView.as_view()),

    path("prescriptions/", PrescriptionListCreateView.as_view()),
    path("prescriptions/<int:pk>/", PrescriptionDetailView.as_view()),

    path("prescription-items/", PrescriptionItemListCreateView.as_view()),
    path(
        "prescription-items/<int:pk>/",
        PrescriptionItemDetailView.as_view(),
    ),

    path("surgery-advice/", SurgeryAdviceListCreateView.as_view()),
    path("surgery-advice/<int:pk>/", SurgeryAdviceDetailView.as_view()),
]
