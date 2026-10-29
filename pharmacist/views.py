# from django.shortcuts import render

# # Create your views here.
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from receptionist.models import Patient
from doctor.models import Prescription
from .serializers import PatientPrescriptionSerializer
from rest_framework import viewsets

from .models import (
    PharmacistProfile,
    MedicineCategory,
    Medicine,
    Supplier,
    InventoryBatch,
    StockMovement,
    MedicinePayment,
)

from .serializers import (
    PharmacistProfileSerializer,
    MedicineCategorySerializer,
    MedicineSerializer,
    SupplierSerializer,
    InventoryBatchSerializer,
    StockMovementSerializer,
    MedicinePaymentSerializer,
)


class PharmacistProfileViewSet(viewsets.ModelViewSet):
    queryset = PharmacistProfile.objects.all()
    serializer_class = PharmacistProfileSerializer


class MedicineCategoryViewSet(viewsets.ModelViewSet):
    queryset = MedicineCategory.objects.all()
    serializer_class = MedicineCategorySerializer


class MedicineViewSet(viewsets.ModelViewSet):
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class InventoryBatchViewSet(viewsets.ModelViewSet):
    queryset = InventoryBatch.objects.all()
    serializer_class = InventoryBatchSerializer


class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer


class MedicinePaymentViewSet(viewsets.ModelViewSet):
    queryset = MedicinePayment.objects.all()
    serializer_class = MedicinePaymentSerializer


class PatientPrescriptionView(APIView):

    def get(self, request):
        patient_number = request.query_params.get("patient_number")

        if not patient_number:
            return Response(
                {"error": "Please provide a patient number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient = get_object_or_404(
            Patient,
            patient_number=patient_number,
        )

        prescriptions = Prescription.objects.filter(
            consultation__appointment__patient=patient
        ).prefetch_related("items__medicine").order_by("-prescribed_at")

        serializer = PatientPrescriptionSerializer(
            prescriptions,
            many=True,
        )

        return Response(serializer.data)