from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


name_validator = RegexValidator(
    regex=r"^[A-Za-z]+(?:[ '-][A-Za-z]+)*$",
    message="Enter a valid name using letters, spaces, apostrophes or hyphens.",
    code="invalid_name",
)


class ReceptionistProfile(models.Model):
    user = models.OneToOneField(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="receptionist_profile",
    )
    employee_id = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.employee_id


class Patient(models.Model):
    patient_number = models.CharField(max_length=20, unique=True,blank=True)
    first_name = models.CharField(max_length=100, validators=[name_validator])
    last_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        if not self.patient_number:
            last_patient = Patient.objects.order_by("-id").first()
            next_id = 1 if last_patient is None else last_patient.id + 1
            self.patient_number = f"P{next_id:03d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_number} - {self.first_name} {self.last_name}".strip()


class Appointment(models.Model):

    class Status(models.TextChoices):
        PAYMENT_PENDING = "PAYMENT_PENDING", "Payment Pending"
        BOOKED = "BOOKED", "Booked"
        CHECKED_IN = "CHECKED_IN", "Checked In"
        IN_CONSULTATION = "IN_CONSULTATION", "In Consultation"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No Show"

    class BookingType(models.TextChoices):
        ADVANCE = "ADVANCE", "Advance Booking"
        WALK_IN = "WALK_IN", "Walk-in"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    doctor = models.ForeignKey(
        "doctor.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PAYMENT_PENDING,
    )
    booking_type = models.CharField(
        max_length=10,
        choices=BookingType.choices,
        default=BookingType.ADVANCE,
    )
    cancellation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["appointment_date", "appointment_time"]

    def __str__(self):
        return f"{self.patient.patient_number} - {self.appointment_date}"


class DailyDoctorQueue(models.Model):
    doctor = models.ForeignKey(
        "doctor.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="daily_queues",
    )
    queue_date = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "queue_date"],
                name="unique_doctor_queue_per_day",
            )
        ]

    def __str__(self):
        return f"{self.doctor.employee_id} - {self.queue_date}"


class QueueToken(models.Model):

    class Status(models.TextChoices):
        WAITING = "WAITING", "Waiting"
        CALLED = "CALLED", "Called"
        IN_CONSULTATION = "IN_CONSULTATION", "In Consultation"
        COMPLETED = "COMPLETED", "Completed"
        SKIPPED = "SKIPPED", "Skipped"
        NO_SHOW = "NO_SHOW", "No Show"
        CANCELLED = "CANCELLED", "Cancelled"

    queue = models.ForeignKey(
        DailyDoctorQueue,
        on_delete=models.PROTECT,
        related_name="tokens",
    )
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.PROTECT,
        related_name="queue_token",
    )
    token_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WAITING,
    )
    checked_in_at = models.DateTimeField(auto_now_add=True)
    called_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["token_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["queue", "token_number"],
                name="unique_token_number_per_queue",
            )
        ]

    @property
    def display_token(self):
        return f"T{self.token_number:03d}"

    def __str__(self):
        return self.display_token


class ConsultationPayment(models.Model):

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        CARD = "CARD", "Card"
        UPI = "UPI", "UPI"
        ONLINE = "ONLINE", "Online"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESSFUL = "SUCCESSFUL", "Successful"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.PROTECT,
        related_name="consultation_payment",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    transaction_reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="consultation_payments_received",
    )

    def __str__(self):
        return f"Appointment {self.appointment_id} - {self.payment_status}"