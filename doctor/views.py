
from datetime import date

from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics
from rest_framework.exceptions import ValidationError, PermissionDenied

from receptionist.models import Appointment
from .models import (
    DoctorProfile,
    DoctorSchedule,
    Consultation,
    ClinicalNote,
    Prescription,
    PrescriptionItem,
    SurgeryAdvice,
)
from .serializers import (
    DoctorDailyAppointmentSerializer,
    DoctorProfileSerializer,
    DoctorScheduleSerializer,
    ConsultationSerializer,
    ClinicalNoteSerializer,
    PrescriptionSerializer,
    PrescriptionItemSerializer,
    SurgeryAdviceSerializer,
)


# 1. Appointments: list all or filter by date/doctor
class DoctorDailyAppointmentsView(generics.ListAPIView):
    serializer_class = DoctorDailyAppointmentSerializer

    def get_queryset(self):
        selected_date = self.request.query_params.get("date")
        doctor_id = self.request.query_params.get("doctor_id")

        if selected_date:
            try:
                selected_date = date.fromisoformat(selected_date)
            except ValueError:
                raise ValidationError({
                    "date": "Use YYYY-MM-DD format."
                })
        else:
            selected_date = timezone.localdate()

        queryset = Appointment.objects.filter(
            appointment_date=selected_date
        )

        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

        return queryset.select_related(
            "patient", "doctor"
        ).order_by("appointment_time")


class DoctorAppointmentDetailView(generics.RetrieveAPIView):
    serializer_class = DoctorDailyAppointmentSerializer
    queryset = Appointment.objects.select_related("patient", "doctor")
    lookup_url_kwarg = "appointment_id"


# 2. Doctor profiles: list or retrieve
class DoctorProfileListView(generics.ListAPIView):
    serializer_class = DoctorProfileSerializer
    queryset = DoctorProfile.objects.select_related("user").all()


class DoctorProfileDetailView(generics.RetrieveAPIView):
    serializer_class = DoctorProfileSerializer
    queryset = DoctorProfile.objects.select_related("user")
    lookup_url_kwarg = "doctor_id"


# 3. Schedules: list or retrieve
class DoctorScheduleListView(generics.ListAPIView):
    serializer_class = DoctorScheduleSerializer

    def get_queryset(self):
        queryset = DoctorSchedule.objects.all()
        doctor_id = self.request.query_params.get("doctor_id")

        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

        return queryset.order_by("day_of_week", "start_time")


class DoctorScheduleDetailView(generics.RetrieveAPIView):
    serializer_class = DoctorScheduleSerializer
    queryset = DoctorSchedule.objects.all()


# 4. Consultations: list/create or retrieve/update
class ConsultationListCreateView(generics.ListCreateAPIView):
    serializer_class = ConsultationSerializer

    def get_queryset(self):
        queryset = Consultation.objects.select_related(
            "appointment", "appointment__patient", "appointment__doctor"
        )
        doctor_id = self.request.query_params.get("doctor_id")

        if doctor_id:
            queryset = queryset.filter(appointment__doctor_id=doctor_id)

        return queryset

    def perform_create(self, serializer):
        appointment = serializer.validated_data["appointment"]

        if Consultation.objects.filter(appointment=appointment).exists():
            raise ValidationError({
                "appointment": "A consultation already exists for this appointment."
            })

        if appointment.status in (
            Appointment.Status.CANCELLED,
            Appointment.Status.NO_SHOW,
            Appointment.Status.COMPLETED,
        ):
            raise ValidationError({
                "appointment": "This appointment cannot start a consultation."
            })

        serializer.save()


class ConsultationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ConsultationSerializer
    queryset = Consultation.objects.select_related("appointment")
    http_method_names = ["get", "put", "patch", "head", "options"]


# 5. Clinical notes: list/create or retrieve
class ClinicalNoteListCreateView(generics.ListCreateAPIView):
    serializer_class = ClinicalNoteSerializer

    def get_queryset(self):
        queryset = ClinicalNote.objects.select_related(
            "consultation", "created_by"
        )
        consultation_id = self.request.query_params.get("consultation_id")

        if consultation_id:
            queryset = queryset.filter(
                consultation_id=consultation_id
            )

        return queryset

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied(
                "Login is required to create clinical notes."
            )

        consultation_id = self.request.data.get("consultation")
        consultation = get_object_or_404(
            Consultation, pk=consultation_id
        )

        serializer.save(
            consultation=consultation,
            created_by=self.request.user,
        )


class ClinicalNoteDetailView(generics.RetrieveAPIView):
    serializer_class = ClinicalNoteSerializer
    queryset = ClinicalNote.objects.select_related(
        "consultation", "created_by"
    )


# 6. Prescriptions: list/create or retrieve
class PrescriptionListCreateView(generics.ListCreateAPIView):
    serializer_class = PrescriptionSerializer

    def get_queryset(self):
        queryset = Prescription.objects.prefetch_related(
            "items__medicine"
        )
        consultation_id = self.request.query_params.get("consultation_id")

        if consultation_id:
            queryset = queryset.filter(
                consultation_id=consultation_id
            )

        return queryset

    def perform_create(self, serializer):
        consultation = serializer.validated_data["consultation"]

        if consultation.status != Consultation.Status.IN_PROGRESS:
            raise ValidationError({
                "consultation": "Consultation must be in progress."
            })

        serializer.save()


class PrescriptionDetailView(generics.RetrieveAPIView):
    serializer_class = PrescriptionSerializer
    queryset = Prescription.objects.prefetch_related("items__medicine")


# 7. Prescription items: list/create or retrieve
class PrescriptionItemListCreateView(generics.ListCreateAPIView):
    serializer_class = PrescriptionItemSerializer

    def get_queryset(self):
        queryset = PrescriptionItem.objects.select_related(
            "prescription", "medicine"
        )
        prescription_id = self.request.query_params.get("prescription_id")

        if prescription_id:
            queryset = queryset.filter(
                prescription_id=prescription_id
            )

        return queryset

    def perform_create(self, serializer):
        prescription = serializer.validated_data["prescription"]

        if prescription.status != Prescription.Status.ACTIVE:
            raise ValidationError({
                "prescription": "Prescription must be active."
            })

        serializer.save()


class PrescriptionItemDetailView(generics.RetrieveAPIView):
    serializer_class = PrescriptionItemSerializer
    queryset = PrescriptionItem.objects.select_related(
        "prescription", "medicine"
    )


# 8. Surgery advice: list/create or retrieve
class SurgeryAdviceListCreateView(generics.ListCreateAPIView):
    serializer_class = SurgeryAdviceSerializer

    def get_queryset(self):
        queryset = SurgeryAdvice.objects.select_related("consultation")
        consultation_id = self.request.query_params.get("consultation_id")

        if consultation_id:
            queryset = queryset.filter(
                consultation_id=consultation_id
            )

        return queryset


class SurgeryAdviceDetailView(generics.RetrieveAPIView):
    serializer_class = SurgeryAdviceSerializer
    queryset = SurgeryAdvice.objects.select_related("consultation")
