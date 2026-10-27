
from rest_framework import serializers
from .models import Patient


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
        read_only_fields = ["id", "patient_number","created_at"]

    def validate_patient_number(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Patient number is required."
            )

        return value

    def validate_phone_number(self, value):
        value = value.strip()

        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError(
                "Enter a valid 10-digit phone number."
            )

        return value

    def validate_first_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "First name is required."
            )

        return value
