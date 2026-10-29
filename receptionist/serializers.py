from datetime import date, datetime, timedelta
from rest_framework import serializers
from .models import Patient

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from .models import Appointment, QueueToken, ConsultationPayment
from django.utils import timezone
from rest_framework import serializers
from doctor.models import DoctorSchedule
from rest_framework import serializers
from doctor.models import DoctorProfile

class PatientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Patient
        fields = [
            "id",
            "patient_number",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "phone_number",
            "email",
            "address",
            "created_at",
        ]
        read_only_fields = ["id", "patient_number", "created_at"]

    def validate_first_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "First name is required."
            )

        return value

    def validate_last_name(self, value):
        return value.strip()

    def validate_date_of_birth(self, value):
        if value > date.today():
            raise serializers.ValidationError(
                "Date of birth cannot be in the future."
            )

        return value

    def validate_gender(self, value):
        value = value.strip().capitalize()
        allowed_genders = ["Male", "Female", "Other"]

        if value not in allowed_genders:
            raise serializers.ValidationError(
                "Gender must be Male, Female, or Other."
            )

        return value

    def validate_phone_number(self, value):
        value = value.strip()

        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError(
                "Enter a valid 10-digit phone number."
            )

        return value
    def validate_email(self, value):
        value = value.strip().lower()

        if value and "@" not in value:
            raise serializers.ValidationError(
            "Enter a valid email address."
        )

        return value

    def validate(self, attrs):
        # Business rule (SRS: "avoid duplicate patient registrations"):
        # patient_number is auto-generated, so it cannot detect the same person
        # being registered twice. Treat same first name + date of birth + phone
        # as a duplicate. Only checked on registration, not on updates.
        if self.instance is None:
            duplicate = Patient.objects.filter(
                first_name__iexact=attrs.get("first_name", ""),
                date_of_birth=attrs.get("date_of_birth"),
                phone_number=attrs.get("phone_number", ""),
            ).first()
            if duplicate:
                raise serializers.ValidationError({
                    "non_field_errors": [
                        f"This patient is already registered as {duplicate.patient_number}."
                    ]
                })
        return attrs

class ReceptionistTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        # Validate the username and password first
        data = super().validate(attrs)

        # Allow only users who have a receptionist profile
        if not hasattr(self.user, "receptionist_profile"):
            raise AuthenticationFailed(
                "Access denied. Receptionist account required."
            )
        return data
#-------------appointment serializer
#--------------------------------------
class AppointmentBookingSerializer(serializers.ModelSerializer):
    # Return the generated patient number in the API response.
    patient_number = serializers.CharField(
        source="patient.patient_number",
        read_only=True,
    )

    # Return the doctor's employee ID in the API response.
    doctor_employee_id = serializers.CharField(
        source="doctor.employee_id",
        read_only=True,
    )

    # Convenience fields so the receptionist screen needs no extra lookups.
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    token = serializers.SerializerMethodField()

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}".strip()

    def get_doctor_name(self, obj):
        return obj.doctor.user.get_full_name() or obj.doctor.user.username

    def get_token(self, obj):
        # hasattr is False when the reverse one-to-one token does not exist yet.
        return obj.queue_token.display_token if hasattr(obj, "queue_token") else None

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "patient_number",
            "patient_name",
            "doctor",
            "doctor_employee_id",
            "doctor_name",
            "appointment_date",
            "appointment_time",
            "booking_type",
            "status",
            "cancellation_reason",
            "token",
            "created_at",
        ]

        # The receptionist must not set the appointment status directly.
        read_only_fields = [
            "id",
            "patient_number",
            "doctor_employee_id",
            "status",
            "cancellation_reason",
            "created_at",
        ]

    def validate(self, attrs):
        # Use submitted values, falling back to existing values for updates.
        appointment_date = attrs.get(
            "appointment_date",
            getattr(self.instance, "appointment_date", None),
        )
        appointment_time = attrs.get(
            "appointment_time",
            getattr(self.instance, "appointment_time", None),
        )
        doctor = attrs.get(
            "doctor",
            getattr(self.instance, "doctor", None),
        )

        if not doctor or not appointment_date or not appointment_time:
            return attrs

        # Do not allow bookings for doctors who are not accepting bookings.
        if not doctor.accepting_bookings:
            raise serializers.ValidationError({
                "doctor": "This doctor is not currently accepting bookings."
            })

        # Do not allow past dates.
        today = timezone.localdate()
        if appointment_date < today:
            raise serializers.ValidationError({
                "appointment_date": "Choose today or a future date."
            })

        # Do not allow times that have already passed today.
        # Get the current local time without timezone information.
        now = timezone.localtime().replace(tzinfo=None).time()
        if appointment_date == today and appointment_time <= now:
            raise serializers.ValidationError({
                "appointment_time": "Choose a future time."
            })

        # Find the schedule that applies on the selected date.
        schedule = DoctorSchedule.objects.filter(
            doctor=doctor,
            day_of_week=appointment_date.weekday(),
            effective_from__lte=appointment_date,
        ).order_by("-effective_from").first()

        if not schedule:
            raise serializers.ValidationError({
                "appointment_date":
                    "This doctor has no schedule for the selected date."
            })

        # Calculate the appointment duration from the doctor's profile.
        duration = doctor.consultation_duration_minutes

        if duration <= 0:
            raise serializers.ValidationError({
                "doctor": "The doctor's consultation duration is invalid."
            })

        # Convert times into datetimes so we can check the whole appointment.
        slot_start = datetime.combine(
            appointment_date,
            appointment_time,
        )
        schedule_start = datetime.combine(
            appointment_date,
            schedule.start_time,
        )
        schedule_end = datetime.combine(
            appointment_date,
            schedule.end_time,
        )
        slot_end = slot_start + timedelta(minutes=duration)

        # The complete appointment must fit inside working hours.
        if (
            slot_start < schedule_start
            or slot_end > schedule_end
        ):
            raise serializers.ValidationError({
                "appointment_time":
                    "The appointment must fit within the doctor's working hours."
            })

        # Appointment start times must align with the schedule's slot intervals.
        elapsed_seconds = (slot_start - schedule_start).total_seconds()
        interval_seconds = duration * 60

        if elapsed_seconds < 0 or elapsed_seconds % interval_seconds != 0:
            raise serializers.ValidationError({
                "appointment_time":
                    "Choose a time offered by the doctor's schedule."
            })

        # A patient must not hold two active bookings with the same doctor on one day.
        patient = attrs.get("patient", getattr(self.instance, "patient", None))
        inactive = [Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW]
        duplicate = Appointment.objects.filter(
            patient=patient, doctor=doctor, appointment_date=appointment_date,
        ).exclude(status__in=inactive)
        if self.instance:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise serializers.ValidationError({
                "patient": "This patient already has an active appointment with this doctor on that date."
            })

        # Exclude cancelled appointments when checking availability.
        overlapping = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
        ).exclude(
            status__in=inactive,
        )

        # Ignore the current appointment if it is being updated.
        if self.instance:
            overlapping = overlapping.exclude(pk=self.instance.pk)

        # Check overlapping appointment durations, not just identical start times.
        for existing in overlapping:
            existing_start = datetime.combine(
                existing.appointment_date,
                existing.appointment_time,
            )
            existing_end = existing_start + timedelta(
                minutes=existing.doctor.consultation_duration_minutes,
            )

            if slot_start < existing_end and slot_end > existing_start:
                raise serializers.ValidationError({
                    "appointment_time":
                        "This time overlaps an existing appointment. Choose another slot."
                })

        return attrs

from doctor.models import DoctorProfile


class BookingDoctorSerializer(serializers.ModelSerializer):
    # Display the doctor's full name in the dropdown.
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = [
            "id",
            "employee_id",
            "doctor_name",
            "specialization",
            "consultation_fee",
            "consultation_duration_minutes",
        ]

    def get_doctor_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class AppointmentRescheduleSerializer(AppointmentBookingSerializer):
    """Reschedule only: patient, doctor and booking type cannot be changed.

    Reuses every availability/conflict rule from AppointmentBookingSerializer.validate().
    """

    class Meta(AppointmentBookingSerializer.Meta):
        read_only_fields = AppointmentBookingSerializer.Meta.read_only_fields + [
            "patient",
            "doctor",
            "booking_type",
        ]


class AppointmentCancelSerializer(serializers.Serializer):
    # SRS: cancellation reason must be stored; we make it mandatory.
    cancellation_reason = serializers.CharField(max_length=500)

    def validate_cancellation_reason(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A cancellation reason is required.")
        return value


class QueueTokenSerializer(serializers.ModelSerializer):
    token = serializers.CharField(source="display_token", read_only=True)
    appointment_id = serializers.IntegerField(source="appointment.id", read_only=True)
    patient_number = serializers.CharField(source="appointment.patient.patient_number", read_only=True)
    patient_name = serializers.SerializerMethodField()
    doctor_id = serializers.IntegerField(source="queue.doctor_id", read_only=True)
    queue_date = serializers.DateField(source="queue.queue_date", read_only=True)

    class Meta:
        model = QueueToken
        fields = [
            "id", "token", "token_number", "status", "queue_date", "doctor_id",
            "appointment_id", "patient_number", "patient_name",
            "checked_in_at", "called_at",
        ]

    def get_patient_name(self, obj):
        p = obj.appointment.patient
        return f"{p.first_name} {p.last_name}".strip()


class ConsultationPaymentSerializer(serializers.ModelSerializer):
    # Amount is optional: it defaults to the doctor's consultation_fee.
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, min_value=0,
    )
    # The receptionist records the outcome; PENDING/REFUNDED are not settable here
    # (refunds need an authorisation rule the SRS has not defined yet).
    payment_status = serializers.ChoiceField(
        choices=[
            ConsultationPayment.PaymentStatus.SUCCESSFUL,
            ConsultationPayment.PaymentStatus.FAILED,
        ],
        default=ConsultationPayment.PaymentStatus.SUCCESSFUL,
    )

    class Meta:
        model = ConsultationPayment
        fields = [
            "id", "appointment", "amount", "payment_method", "payment_status",
            "transaction_reference", "paid_at", "received_by",
        ]
        read_only_fields = ["id", "appointment", "paid_at", "received_by"]

    def validate(self, attrs):
        # Online payments must carry the provider's reference.
        method = attrs.get("payment_method")
        reference = attrs.get("transaction_reference", "").strip()
        if method == ConsultationPayment.PaymentMethod.ONLINE and not reference:
            raise serializers.ValidationError({
                "transaction_reference": "Required for online payments."
            })
        attrs["transaction_reference"] = reference
        return attrs