from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from doctor.models import DoctorProfile

from .auth import IsReceptionist
from .models import (
    Appointment,
    ConsultationPayment,
    DailyDoctorQueue,
    Patient,
    QueueToken,
)
from .serializers import (
    AppointmentBookingSerializer,
    AppointmentCancelSerializer,
    AppointmentRescheduleSerializer,
    BookingDoctorSerializer,
    ConsultationPaymentSerializer,
    PatientSerializer,
    QueueTokenSerializer,
    ReceptionistTokenObtainPairSerializer,
)

# Statuses from which a patient may be checked in. PAYMENT_PENDING is allowed so
# the receptionist can take payment at the desk (SRS: "records payment when required").
# Change this one tuple if the clinic requires payment before check-in.
CHECK_IN_ELIGIBLE = (Appointment.Status.PAYMENT_PENDING, Appointment.Status.BOOKED)
# Statuses that may still be rescheduled / cancelled by the receptionist.
CHANGEABLE = (Appointment.Status.PAYMENT_PENDING, Appointment.Status.BOOKED)
CANCELLABLE = CHANGEABLE + (Appointment.Status.CHECKED_IN,)


def parse_date_param(value, field="date"):
    """Parse YYYY-MM-DD from a query string; 400 on bad input."""
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError({field: "Use YYYY-MM-DD format."})


def lock_doctor(doctor_id):
    """Serialise bookings per doctor so two requests cannot take the same slot.

    select_for_update() holds a row lock until the surrounding transaction ends
    (effective on MySQL/InnoDB). Invalid ids are ignored here; the serializer
    reports them properly.
    """
    try:
        DoctorProfile.objects.select_for_update().filter(pk=int(doctor_id)).first()
    except (TypeError, ValueError):
        pass


# ---------------------------------------------------------------- UC-01 Login
class ReceptionistLoginView(TokenObtainPairView):
    serializer_class = ReceptionistTokenObtainPairSerializer


# ------------------------------------------------------- UC-02 / UC-03 Patients
class PatientListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = PatientSerializer
    permission_classes = [IsReceptionist]

    def get_queryset(self):
        queryset = Patient.objects.all().order_by("-created_at")
        search = self.request.query_params.get("search", "").strip()

        if search:
            conditions = (
                Q(patient_number__iexact=search)
                | Q(phone_number__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
            if search.isdigit():
                conditions |= Q(id=int(search))
            queryset = queryset.filter(conditions)

        return queryset


class PatientDetailUpdateAPIView(generics.RetrieveUpdateAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsReceptionist]


# ------------------------------------------------------------ UC-04 Doctors
class BookingDoctorDropdownAPIView(generics.ListAPIView):
    serializer_class = BookingDoctorSerializer
    permission_classes = [IsAuthenticated, IsReceptionist]

    def get_queryset(self):
        today = timezone.localdate()
        return (
            DoctorProfile.objects
            .filter(accepting_bookings=True, schedules__effective_from__lte=today)
            .select_related("user")
            .distinct()
            .order_by("user__first_name", "user__last_name")
        )


# --------------------------------------------- UC-04 Book / list appointments
class AppointmentListCreateAPIView(generics.ListCreateAPIView):
    """GET filters: ?patient=<id>&doctor=<id>&date=YYYY-MM-DD&status=BOOKED"""
    serializer_class = AppointmentBookingSerializer
    permission_classes = [IsReceptionist]

    def get_queryset(self):
        params = self.request.query_params
        qs = Appointment.objects.select_related(
            "patient", "doctor__user", "queue_token"
        )

        for key in ("patient", "doctor"):
            value = params.get(key)
            if value:
                if not value.isdigit():
                    raise ValidationError({key: "Must be a numeric ID."})
                qs = qs.filter(**{f"{key}_id": int(value)})

        if params.get("date"):
            qs = qs.filter(appointment_date=parse_date_param(params["date"]))

        if params.get("status"):
            wanted = params["status"].upper()
            if wanted not in Appointment.Status.values:
                raise ValidationError({
                    "status": f"Choose one of: {', '.join(Appointment.Status.values)}."
                })
            qs = qs.filter(status=wanted)

        return qs

    def create(self, request, *args, **kwargs):
        # Lock the doctor row first so the conflict check + insert are atomic.
        with transaction.atomic():
            lock_doctor(request.data.get("doctor"))
            return super().create(request, *args, **kwargs)


# ------------------------------------------ UC-05 View / reschedule appointment
class AppointmentDetailRescheduleAPIView(generics.RetrieveUpdateAPIView):
    """GET one appointment; PATCH appointment_date/appointment_time to reschedule."""
    queryset = Appointment.objects.select_related("patient", "doctor__user")
    serializer_class = AppointmentRescheduleSerializer
    permission_classes = [IsReceptionist]
    http_method_names = ["get", "patch", "head", "options"]  # no full PUT

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            appointment = self.get_object()
            lock_doctor(appointment.doctor_id)
            # Re-read inside the lock so the status check is current.
            appointment.refresh_from_db()
            if appointment.status not in CHANGEABLE:
                raise ValidationError({
                    "status": f"A {appointment.status} appointment cannot be rescheduled."
                })
            return super().update(request, *args, **kwargs)


class AppointmentCancelAPIView(APIView):
    """POST {"cancellation_reason": "..."} -> status CANCELLED."""
    permission_classes = [IsReceptionist]

    def post(self, request, pk):
        serializer = AppointmentCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            appointment = get_object_or_404(
                Appointment.objects.select_for_update(), pk=pk
            )
            if appointment.status not in CANCELLABLE:
                raise ValidationError({
                    "status": f"A {appointment.status} appointment cannot be cancelled."
                })

            appointment.status = Appointment.Status.CANCELLED
            appointment.cancellation_reason = serializer.validated_data["cancellation_reason"]
            appointment.save(update_fields=["status", "cancellation_reason"])

            # SRS: keep the queue accurate if the patient had already checked in.
            QueueToken.objects.filter(appointment=appointment).update(
                status=QueueToken.Status.CANCELLED
            )

        return Response(
            AppointmentBookingSerializer(appointment).data, status=status.HTTP_200_OK
        )


# ------------------------------------------------ UC-06 Check-in and token
class AppointmentCheckInAPIView(APIView):
    """POST (no body): check in an appointment and issue the next queue token."""
    permission_classes = [IsReceptionist]

    def post(self, request, pk):
        with transaction.atomic():
            # Lock the appointment so a double-click cannot create two tokens.
            appointment = get_object_or_404(
                Appointment.objects.select_for_update(), pk=pk
            )

            if appointment.status == Appointment.Status.CANCELLED:
                raise ValidationError({"status": "Cancelled appointments cannot be checked in."})

            # Repeat request: return the existing token instead of creating another.
            existing = QueueToken.objects.filter(appointment=appointment).first()
            if existing:
                return Response(
                    {"message": "Patient is already checked in.",
                     "token": QueueTokenSerializer(existing).data},
                    status=status.HTTP_200_OK,
                )

            if appointment.status not in CHECK_IN_ELIGIBLE:
                raise ValidationError({
                    "status": f"A {appointment.status} appointment cannot be checked in."
                })

            if appointment.appointment_date != timezone.localdate():
                raise ValidationError({
                    "appointment_date": "Check-in is only allowed on the appointment date."
                })

            # One queue per doctor per day (DB unique constraint makes this race-safe).
            queue, _ = DailyDoctorQueue.objects.get_or_create(
                doctor=appointment.doctor, queue_date=appointment.appointment_date,
            )
            # Lock the queue row, then take max+1: concurrent check-ins for the
            # same doctor queue up here, so token numbers never collide.
            queue = DailyDoctorQueue.objects.select_for_update().get(pk=queue.pk)
            last = queue.tokens.aggregate(m=Max("token_number"))["m"] or 0

            token = QueueToken.objects.create(
                queue=queue, appointment=appointment, token_number=last + 1,
            )
            # Token creation and status update commit together or not at all.
            appointment.status = Appointment.Status.CHECKED_IN
            appointment.save(update_fields=["status"])

        return Response(
            {"message": "Patient checked in.", "token": QueueTokenSerializer(token).data},
            status=status.HTTP_201_CREATED,
        )


class QueueListAPIView(generics.ListAPIView):
    """GET ?date=YYYY-MM-DD (default today)&doctor=<id>: tokens in queue order."""
    serializer_class = QueueTokenSerializer
    permission_classes = [IsReceptionist]

    def get_queryset(self):
        params = self.request.query_params
        queue_date = (
            parse_date_param(params["date"]) if params.get("date")
            else timezone.localdate()
        )
        qs = QueueToken.objects.filter(queue__queue_date=queue_date).select_related(
            "queue", "appointment__patient"
        ).order_by("queue__doctor_id", "token_number")

        if params.get("doctor"):
            if not params["doctor"].isdigit():
                raise ValidationError({"doctor": "Must be a numeric ID."})
            qs = qs.filter(queue__doctor_id=int(params["doctor"]))
        return qs


# ------------------------------------------------------- UC-07 Payment
class AppointmentPaymentAPIView(APIView):
    """GET the payment for an appointment; POST to record it.

    POST body: {"payment_method": "CASH|CARD|UPI|ONLINE", "amount": "500.00" (optional,
    defaults to the doctor's fee), "payment_status": "SUCCESSFUL|FAILED" (default
    SUCCESSFUL), "transaction_reference": "..." (required for ONLINE)}
    """
    permission_classes = [IsReceptionist]

    def get(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        payment = ConsultationPayment.objects.filter(appointment=appointment).first()
        if not payment:
            return Response({"detail": "No payment recorded for this appointment."},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(ConsultationPaymentSerializer(payment).data)

    def post(self, request, pk):
        serializer = ConsultationPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            appointment = get_object_or_404(
                Appointment.objects.select_for_update().select_related("doctor"), pk=pk
            )
            if appointment.status in (
                Appointment.Status.CANCELLED,
                Appointment.Status.NO_SHOW,
                Appointment.Status.COMPLETED,
            ):
                raise ValidationError({
                    "status": f"Cannot record payment for a {appointment.status} appointment."
                })

            payment = ConsultationPayment.objects.filter(appointment=appointment).first()
            # Prevent duplicate successful payments (SRS UC-07).
            if payment and payment.payment_status == ConsultationPayment.PaymentStatus.SUCCESSFUL:
                return Response({"detail": "A successful payment already exists."},
                                status=status.HTTP_409_CONFLICT)

            is_success = data["payment_status"] == ConsultationPayment.PaymentStatus.SUCCESSFUL
            fields = dict(
                amount=data.get("amount", appointment.doctor.consultation_fee),
                payment_method=data["payment_method"],
                payment_status=data["payment_status"],
                transaction_reference=data["transaction_reference"],
                paid_at=timezone.now() if is_success else None,
                received_by=request.user,
            )
            if payment:  # a previous FAILED/PENDING attempt is retried in place
                for k, v in fields.items():
                    setattr(payment, k, v)
                payment.save()
            else:
                payment = ConsultationPayment.objects.create(appointment=appointment, **fields)

            # Paid appointments become confirmed.
            if is_success and appointment.status == Appointment.Status.PAYMENT_PENDING:
                appointment.status = Appointment.Status.BOOKED
                appointment.save(update_fields=["status"])

        return Response(ConsultationPaymentSerializer(payment).data,
                        status=status.HTTP_201_CREATED)


# ------------------------------------------------------- UC-08 Daily report
class DailyReportAPIView(APIView):
    """GET ?date=YYYY-MM-DD (default today). Empty days return zero counts."""
    permission_classes = [IsReceptionist]

    def get(self, request):
        raw = request.query_params.get("date")
        report_date = parse_date_param(raw) if raw else timezone.localdate()

        appointments = Appointment.objects.filter(appointment_date=report_date)
        payments = ConsultationPayment.objects.filter(
            appointment__appointment_date=report_date
        )
        tokens = QueueToken.objects.filter(queue__queue_date=report_date)

        # Every status appears in the output, even with a zero count.
        by_status = {s: 0 for s in Appointment.Status.values}
        for row in appointments.values("status").annotate(n=Count("id")):
            by_status[row["status"]] = row["n"]

        successful = payments.filter(
            payment_status=ConsultationPayment.PaymentStatus.SUCCESSFUL
        ).aggregate(count=Count("id"), total=Sum("amount"))

        # Active appointments with no successful payment yet.
        awaiting_payment = (
            appointments
            .exclude(status__in=[Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW])
            .exclude(consultation_payment__payment_status=ConsultationPayment.PaymentStatus.SUCCESSFUL)
            .count()
        )

        # Doctor-wise appointment and token counts.
        doctors = {}
        for row in appointments.values("doctor_id", "doctor__employee_id").annotate(n=Count("id")):
            doctors[row["doctor_id"]] = {
                "doctor_id": row["doctor_id"],
                "employee_id": row["doctor__employee_id"],
                "appointments": row["n"],
                "tokens_issued": 0,
            }
        for row in tokens.values("queue__doctor_id").annotate(n=Count("id")):
            if row["queue__doctor_id"] in doctors:
                doctors[row["queue__doctor_id"]]["tokens_issued"] = row["n"]

        return Response({
            "date": report_date.isoformat(),
            "total_appointments": appointments.count(),
            "appointments_by_status": by_status,
            "patients_registered": Patient.objects.filter(created_at__date=report_date).count(),
            "check_ins": tokens.count(),
            "payments": {
                "successful_count": successful["count"],
                # Always two decimals, whatever the database backend returns.
                "successful_total": f'{Decimal(successful["total"] or 0):.2f}',
                "failed_count": payments.filter(
                    payment_status=ConsultationPayment.PaymentStatus.FAILED).count(),
                "appointments_awaiting_payment": awaiting_payment,
            },
            "doctors": list(doctors.values()),
        })