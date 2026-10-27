
from rest_framework import serializers

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


# 1. Doctor's daily appointment list
class DoctorDailyAppointmentSerializer(serializers.ModelSerializer):
    patient_number = serializers.CharField(
        source="patient.patient_number",
        read_only=True,
    )

    patient_name = serializers.SerializerMethodField()

    doctor_employee_id = serializers.CharField(
        source="doctor.employee_id",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    booking_type_display = serializers.CharField(
        source="get_booking_type_display",
        read_only=True,
    )

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient_number",
            "patient_name",
            "doctor_employee_id",
            "appointment_date",
            "appointment_time",
            "status",
            "status_display",
            "booking_type",
            "booking_type_display",
        ]
        read_only_fields = fields

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}".strip()


# 2. Doctor profile
class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = "__all__"
        read_only_fields = ("id", "employee_id")


# 3. Doctor's working schedule
class DoctorScheduleSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(
        source="get_day_of_week_display",
        read_only=True,
    )

    class Meta:
        model = DoctorSchedule
        fields = [
            "id",
            "doctor",
            "day_of_week",
            "day_name",
            "start_time",
            "end_time",
            "effective_from",
        ]
        read_only_fields = ("id",)


# 4. Consultation
class ConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultation
        fields = "__all__"
        read_only_fields = ("id", "started_at")


# 5. Clinical notes
class ClinicalNoteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    class Meta:
        model = ClinicalNote
        fields = [
            "id",
            "consultation",
            "note",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = (
            "id",
            "created_by",
            "created_at",
        )


# 6. Prescription item summary
# Used when displaying prescription items inside a prescription.
# This avoids recursive/nested serializer references.
class PrescriptionItemSummarySerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="medicine.name",
        read_only=True,
    )

    class Meta:
        model = PrescriptionItem
        fields = [
            "id",
            "medicine",
            "medicine_name",
            "dosage",
            "frequency",
            "duration_days",
            "quantity",
            "instructions",
        ]
        read_only_fields = fields


# 7. Prescription item create/update representation
class PrescriptionItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="medicine.name",
        read_only=True,
    )

    class Meta:
        model = PrescriptionItem
        fields = [
            "id",
            "prescription",
            "medicine",
            "medicine_name",
            "dosage",
            "frequency",
            "duration_days",
            "quantity",
            "instructions",
        ]
        read_only_fields = ("id", "medicine_name")


# 8. Prescription
class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSummarySerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Prescription
        fields = [
            "id",
            "consultation",
            "prescribed_at",
            "instructions",
            "status",
            "items",
        ]
        read_only_fields = ("id", "prescribed_at", "items")


# 9. Surgery advice
class SurgeryAdviceSerializer(serializers.ModelSerializer):
    urgency_display = serializers.CharField(
        source="get_urgency_display",
        read_only=True,
    )

    class Meta:
        model = SurgeryAdvice
        fields = [
            "id",
            "consultation",
            "procedure_name",
            "urgency",
            "urgency_display",
            "suggested_date",
        ]
        read_only_fields = ("id",)
