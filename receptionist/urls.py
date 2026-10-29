from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AppointmentCancelAPIView,
    AppointmentCheckInAPIView,
    AppointmentDetailRescheduleAPIView,
    AppointmentListCreateAPIView,
    AppointmentPaymentAPIView,
    BookingDoctorDropdownAPIView,
    DailyReportAPIView,
    PatientDetailUpdateAPIView,
    PatientListCreateAPIView,
    QueueListAPIView,
    ReceptionistLoginView,
)

urlpatterns = [
    # UC-01 login (JWT) + refresh
    path("receptionist/login/", ReceptionistLoginView.as_view(), name="receptionist-login"),
    path("receptionist/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # UC-02 / UC-03 patients
    path("patients/", PatientListCreateAPIView.as_view(), name="patient-list-create"),
    path("patients/<int:pk>/", PatientDetailUpdateAPIView.as_view(), name="patient-detail-update"),

    # UC-04 booking (doctor dropdown + appointments)
    path("booking-doctors/", BookingDoctorDropdownAPIView.as_view(), name="booking-doctors"),
    path("appointments/", AppointmentListCreateAPIView.as_view(), name="appointment-list-create"),

    # UC-05 reschedule / cancel
    path("appointments/<int:pk>/", AppointmentDetailRescheduleAPIView.as_view(), name="appointment-detail"),
    path("appointments/<int:pk>/cancel/", AppointmentCancelAPIView.as_view(), name="appointment-cancel"),

    # UC-06 check-in + queue
    path("appointments/<int:pk>/check-in/", AppointmentCheckInAPIView.as_view(), name="appointment-check-in"),
    path("queue/", QueueListAPIView.as_view(), name="queue-list"),

    # UC-07 payment
    path("appointments/<int:pk>/payment/", AppointmentPaymentAPIView.as_view(), name="appointment-payment"),

    # UC-08 report
    path("reports/daily/", DailyReportAPIView.as_view(), name="daily-report"),
]