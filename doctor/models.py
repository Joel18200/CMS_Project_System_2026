from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="doctor_profile",
    )
    employee_id = models.CharField(max_length=20, unique=True,blank=True,)
    specialization = models.CharField(max_length=100)
    qualification = models.CharField(max_length=150)
    registration_number = models.CharField(max_length=50, unique=True)
    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    consultation_duration_minutes = models.PositiveIntegerField(
        default=15,
        validators=[MinValueValidator(1)],
    )
    accepting_bookings = models.BooleanField(default=True)
    def save(self, *args, **kwargs):
        if not self.employee_id:
            last_doctor = DoctorProfile.objects.order_by("-id").first()
            next_id = 1 if last_doctor is None else last_doctor.id + 1
            self.employee_id = f"D{next_id:03d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()}"


class DoctorSchedule(models.Model):

    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    day_of_week = models.IntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    effective_from = models.DateField()

    def clean(self):
        super().clean()

        if (
            self.start_time
            and self.end_time
            and self.end_time <= self.start_time
        ):
            raise ValidationError({
                "end_time": "End time must be later than start time."
            })

    class Meta:
        ordering = ["day_of_week", "start_time"]

    def __str__(self):
        return (
            f"{self.doctor.employee_id} - "
            f"{self.get_day_of_week_display()}"
        )


class Consultation(models.Model):

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"

    appointment = models.OneToOneField(
        "receptionist.Appointment",
        on_delete=models.PROTECT,
        related_name="consultation",
    )
    diagnosis = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )

    def clean(self):
        super().clean()

        if (
            self.completed_at
            and self.started_at
            and self.completed_at < self.started_at
        ):
            raise ValidationError({
                "completed_at": "Completion time cannot precede start time."
            })

    def __str__(self):
        return f"Consultation {self.pk}"


class ClinicalNote(models.Model):
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.PROTECT,
        related_name="clinical_notes",
    )
    note = models.TextField()
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="clinical_notes_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Clinical Note {self.pk}"


class Prescription(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DISPENSED = "DISPENSED", "Dispensed"
        CANCELLED = "CANCELLED", "Cancelled"

    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.PROTECT,
        related_name="prescriptions",
    )

    medicines = models.ManyToManyField(
        "pharmacist.Medicine",
        through="PrescriptionItem",
        related_name="prescriptions",
    )

    prescribed_at = models.DateTimeField(auto_now_add=True)
    instructions = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    def __str__(self):
        return f"Prescription {self.pk}"


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name="items",
    )
    medicine = models.ForeignKey(
        "pharmacist.Medicine",
        on_delete=models.PROTECT,
        related_name="prescription_items",
    )
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration_days = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    instructions = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["prescription", "medicine"],
                name="unique_medicine_per_prescription",
            )
        ]

    def __str__(self):
        return (
            f"Prescription {self.prescription_id} - "
            f"{self.medicine.name}"
        )


class SurgeryAdvice(models.Model):

    class Urgency(models.TextChoices):
        ROUTINE = "ROUTINE", "Routine"
        URGENT = "URGENT", "Urgent"
        EMERGENCY = "EMERGENCY", "Emergency"

    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.PROTECT,
        related_name="surgery_advices",
    )
    procedure_name = models.CharField(max_length=200)
    urgency = models.CharField(
        max_length=10,
        choices=Urgency.choices,
        default=Urgency.ROUTINE,
    )
    suggested_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.procedure_name