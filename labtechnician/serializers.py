
from rest_framework import serializers
from .models import (
    LabTechnicianProfile,
    LabTest,
    LabOrder,
    LabResult,
)


class LabTechnicianProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTechnicianProfile
        fields = "__all__"


class LabTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTest
        fields = "__all__"


class LabOrderSerializer(serializers.ModelSerializer):
    test_name = serializers.CharField(
        source="lab_test.name",
        read_only=True,
    )

    class Meta:
        model = LabOrder
        fields = "__all__"


class LabResultSerializer(serializers.ModelSerializer):
    test_name = serializers.CharField(
        source="lab_order.lab_test.name",
        read_only=True,
    )
    order_id = serializers.IntegerField(
        source="lab_order.id",
        read_only=True,
    )
    order_status = serializers.CharField(
        source="lab_order.status",
        read_only=True,
    )

    class Meta:
        model = LabResult
        fields = "__all__"
