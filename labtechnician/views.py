
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from .models import (
    LabTechnicianProfile,
    LabTest,
    LabOrder,
    LabResult,
)

from .serializers import (
    LabTechnicianProfileSerializer,
    LabTestSerializer,
    LabOrderSerializer,
    LabResultSerializer,
)


class LabTechnicianProfileViewSet(viewsets.ModelViewSet):
    queryset = LabTechnicianProfile.objects.all()
    serializer_class = LabTechnicianProfileSerializer


class LabTestViewSet(viewsets.ModelViewSet):
    queryset = LabTest.objects.all()
    serializer_class = LabTestSerializer


class LabOrderViewSet(viewsets.ModelViewSet):
    queryset = LabOrder.objects.all()
    serializer_class = LabOrderSerializer


class LabResultViewSet(viewsets.ModelViewSet):
    queryset = LabResult.objects.all()
    serializer_class = LabResultSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def today_lab_orders(request):
    today = timezone.localdate()

    orders = (
        LabOrder.objects
        .filter(ordered_at__date=today)
        .select_related("lab_test")
        .order_by("ordered_at", "id")
    )

    data = []

    for number, order in enumerate(orders, start=1):
        data.append({
            "order_id": number,
            "test_name": order.lab_test.name,
            "price": str(order.lab_test.price),
            "status": order.status,
            "ordered_at": order.ordered_at,
        })

    return Response({
        "date": str(today),
        "total_orders": len(data),
        "orders": data,
    })
