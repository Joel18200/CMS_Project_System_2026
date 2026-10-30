# from django.shortcuts import render

# # Create your views here.
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from receptionist.models import Patient
from doctor.models import Prescription, PrescriptionItem
from .serializers import PatientPrescriptionSerializer
from rest_framework import viewsets

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

import uuid
from decimal import Decimal

from .models import (
    PharmacistProfile,
    MedicineCategory,
    Medicine,
    Supplier,
    InventoryBatch,
    StockMovement,
    MedicinePayment,
    MedicineBill,
    MedicineBillItem,
)

from .serializers import (
    PharmacistProfileSerializer,
    MedicineCategorySerializer,
    MedicineSerializer,
    SupplierSerializer,
    InventoryBatchSerializer,
    StockMovementSerializer,
    MedicinePaymentSerializer,
    MedicineBillDetailSerializer,
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


class DispensePrescriptionView(APIView):

    def post(self, request):
        prescription_id = request.data.get("prescription_id")

        if not prescription_id:
            return Response(
                {"error": "Please provide a prescription_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Temporary until team authentication is integrated.
        performed_by_id = request.data.get("performed_by_id")

        if not performed_by_id:
            return Response(
                {"error": "Please provide performed_by_id for testing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        User = get_user_model()
        performed_by = User.objects.filter(
            pk=performed_by_id,
            is_active=True,
        ).first()

        if not performed_by:
            return Response(
                {"error": "The specified active user does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():

            prescription = get_object_or_404(
                Prescription.objects.select_for_update(),
                pk=prescription_id,
            )

            if prescription.status != Prescription.Status.ACTIVE:
                return Response(
                    {"error": "Only active prescriptions can be dispensed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Preserve the existing payment requirement.
            try:
                payment = prescription.medicine_payment
            except MedicinePayment.DoesNotExist:
                return Response(
                    {"error": "No payment record exists for this prescription."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if payment.payment_status != MedicinePayment.PaymentStatus.SUCCESSFUL:
                return Response(
                    {"error": "Payment must be successful before dispensing."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            items = list(
                PrescriptionItem.objects.filter(
                    prescription=prescription
                ).select_related("medicine")
            )

            if not items:
                return Response(
                    {"error": "This prescription has no medicines."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            allocations = []
            shortages = []
            all_quantities_fulfilled = True

            # Calculate outstanding quantities and allocate available stock.
            for item in items:

                already_dispensed = (
                    StockMovement.objects.filter(
                        prescription_item=item,
                        movement_type=StockMovement.MovementType.DISPENSED,
                    ).aggregate(total=Sum("quantity_change"))["total"]
                    or 0
                )

                already_dispensed = abs(already_dispensed)
                remaining_required = max(
                    0, item.quantity - already_dispensed
                )

                if remaining_required == 0:
                    continue

                remaining = remaining_required

                batches = list(
                    InventoryBatch.objects.select_for_update()
                    .filter(
                        medicine=item.medicine,
                        expiry_date__gte=timezone.localdate(),
                    )
                    .order_by("expiry_date", "id")
                )

                available_total = 0

                for batch in batches:
                    available = (
                        batch.stock_movements.aggregate(
                            total=Sum("quantity_change")
                        )["total"] or 0
                    )

                    if available <= 0:
                        continue

                    available_total += available

                    quantity_to_dispense = min(available, remaining)

                    allocations.append({
                        "item": item,
                        "batch": batch,
                        "quantity": quantity_to_dispense,
                    })

                    remaining -= quantity_to_dispense

                    if remaining == 0:
                        break

                if remaining > 0:
                    all_quantities_fulfilled = False

                    shortages.append({
                        "medicine": item.medicine.name,
                        "prescribed_quantity": item.quantity,
                        "already_dispensed": already_dispensed,
                        "dispensed_this_time": (
                            remaining_required - remaining
                        ),
                        "available_quantity": available_total,
                        "remaining_quantity": remaining,
                    })

            # Nothing can be dispensed: do not create an empty bill.
            if not allocations:
                return Response(
                    {
                        "error": "No additional quantities are available to dispense.",
                        "shortages": shortages,
                        "doctor_review_required": bool(shortages),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # Record actual dispensing movements.
            movements = []

            for allocation in allocations:
                movement = StockMovement.objects.create(
                    inventory_batch=allocation["batch"],
                    prescription_item=allocation["item"],
                    movement_type=StockMovement.MovementType.DISPENSED,
                    quantity_change=-allocation["quantity"],
                    performed_by=performed_by,
                )

                movements.append((allocation, movement))

            # Calculate this bill from quantities dispensed NOW.
            subtotal = Decimal("0.00")
            bill_lines = []

            for allocation, movement in movements:
                batch = allocation["batch"]
                quantity = allocation["quantity"]

                rate = batch.selling_price_per_unit
                mrp = batch.mrp_per_unit
                line_amount = rate * quantity

                subtotal += line_amount

                bill_lines.append({
                    "allocation": allocation,
                    "movement": movement,
                    "rate": rate,
                    "mrp": mrp,
                    "line_amount": line_amount,
                })

            # A unique bill number for each dispensing transaction.
            bill_number = (
                f"MB-{prescription.id}-"
                f"{uuid.uuid4().hex[:8].upper()}"
            )

            bill = MedicineBill.objects.create(
                bill_number=bill_number,
                prescription=prescription,
                payment=payment,
                subtotal=subtotal,
                discount_amount=Decimal("0.00"),
                tax_amount=Decimal("0.00"),
                total_amount=subtotal,
                dispensed_by=performed_by,
            )

            # One bill line per actual stock movement.
            for line in bill_lines:
                allocation = line["allocation"]
                batch = allocation["batch"]

                MedicineBillItem.objects.create(
                    bill=bill,
                    prescription_item=allocation["item"],
                    inventory_batch=batch,
                    stock_movement=line["movement"],
                    quantity=allocation["quantity"],
                    rate=line["rate"],
                    mrp=line["mrp"],
                    discount_amount=Decimal("0.00"),
                    gst_rate=Decimal("0.00"),
                    cgst_amount=Decimal("0.00"),
                    sgst_amount=Decimal("0.00"),
                    net_amount=line["line_amount"],
                )

            # Keep ACTIVE while any prescribed quantity remains.
            if all_quantities_fulfilled:
                prescription.status = Prescription.Status.DISPENSED
                prescription.save(update_fields=["status"])

        return Response(
            {
                "message": (
                    "Prescription fully dispensed."
                    if all_quantities_fulfilled
                    else "Partial dispensing completed."
                ),
                "prescription_id": prescription.id,
                "prescription_status": prescription.status,
                "bill_number": bill.bill_number,
                "bill_id": bill.id,
                "subtotal": str(bill.subtotal),
                "total_amount": str(bill.total_amount),
                "dispensed_by": performed_by.get_username(),
                "dispensed_items": [
                    {
                        "medicine": line["allocation"]["item"].medicine.name,
                        "batch_number": line["allocation"]["batch"].batch_number,
                        "expiry_date": str(
                            line["allocation"]["batch"].expiry_date
                        ),
                        "quantity": line["allocation"]["quantity"],
                        "rate": str(line["rate"]),
                        "mrp": str(line["mrp"]),
                        "amount": str(line["line_amount"]),
                    }
                    for line in bill_lines
                ],
                "shortages": shortages,
            },
            status=status.HTTP_200_OK,
        )


class MedicineBillDetailView(APIView):
    def get(self, request, bill_id):
        bill = get_object_or_404(
            MedicineBill.objects.select_related(
                "prescription",
                "dispensed_by",
            ).prefetch_related(
                "items__prescription_item__medicine",
                "items__inventory_batch",
            ),
            pk=bill_id,
        )

        serializer = MedicineBillDetailSerializer(bill)
        return Response(serializer.data, status=status.HTTP_200_OK)