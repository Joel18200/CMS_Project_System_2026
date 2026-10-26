from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator


class LabTechnicianProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="labtechnician_profile",
    )
    employee_id = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.employee_id


class LabTest(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    turnaround_time_hours = models.PositiveIntegerField(default=24)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class LabOrder(models.Model):
    class Status(models.TextChoices):
        ORDERED = "ORDERED", "Ordered"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    consultation = models.ForeignKey(
        "doctor.Consultation",
        on_delete=models.PROTECT,
        related_name="lab_orders",
    )
    lab_test = models.ForeignKey(
        LabTest,
        on_delete=models.PROTECT,
        related_name="lab_orders",
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ORDERED,
    )
    ordered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ordered_at"]

    def __str__(self):
        return f"{self.lab_test.name} - Order {self.pk}"


class LabResult(models.Model):
    class ResultStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        COMPLETED = "COMPLETED", "Completed"
        RELEASED = "RELEASED", "Released"

    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending Review"
        REVIEWED = "REVIEWED", "Reviewed"

    lab_order = models.OneToOneField(
        LabOrder,
        on_delete=models.PROTECT,
        related_name="result",
    )
    result_value = models.TextField()
    units = models.CharField(max_length=50, blank=True)
    reference_range = models.CharField(max_length=100, blank=True)
    technician_notes = models.TextField(blank=True)
    result_status = models.CharField(
        max_length=10,
        choices=ResultStatus.choices,
        default=ResultStatus.DRAFT,
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lab_results_recorded",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)
    doctor_review_status = models.CharField(
        max_length=10,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        "doctor.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="reviewed_lab_results",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        super().clean()

        if self.result_status == self.ResultStatus.RELEASED and not self.released_at:
            raise ValidationError({
                "released_at": "A released result must have a release timestamp."
            })

        if self.doctor_review_status == self.ReviewStatus.REVIEWED:
            if not self.reviewed_by or not self.reviewed_at:
                raise ValidationError(
                    "A reviewed result must record the reviewing doctor and review time."
                )

    def __str__(self):
        return f"Result for Lab Order {self.lab_order_id}"
