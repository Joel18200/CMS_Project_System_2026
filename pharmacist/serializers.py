from doctor.models import Prescription, PrescriptionItem
from rest_framework import serializers
from .models import (
    PharmacistProfile,
    MedicineCategory,
    Medicine,
    Supplier,
    InventoryBatch,
    StockMovement,
    MedicinePayment,
)


class PharmacistProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacistProfile
        fields = "__all__"


class MedicineCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineCategory
        fields = "__all__"


class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class InventoryBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryBatch
        fields = "__all__"


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = "__all__"


class MedicinePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicinePayment
        fields = "__all__"

class PrescriptionItemSerializer(serializers.ModelSerializer):
    medicine = MedicineSerializer(read_only=True)

    class Meta:
        model = PrescriptionItem
        fields = [
            "id",
            "medicine",
            "dosage",
            "frequency",
            "duration_days",
            "quantity",
            "instructions",
        ]


class PatientPrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)

    patient_number = serializers.CharField(
        source="consultation.appointment.patient.patient_number",
        read_only=True,
    )

    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = [
            "id",
            "patient_number",
            "patient_name",
            "prescribed_at",
            "instructions",
            "status",
            "items",
        ]

    def get_patient_name(self, obj):
        patient = obj.consultation.appointment.patient
        return f"{patient.first_name} {patient.last_name}".strip()