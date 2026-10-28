from datetime import date
from rest_framework import serializers
from .models import Patient

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
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
