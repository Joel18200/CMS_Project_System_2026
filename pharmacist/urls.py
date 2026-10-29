from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PharmacistProfileViewSet,
    MedicineCategoryViewSet,
    MedicineViewSet,
    SupplierViewSet,
    InventoryBatchViewSet,
    StockMovementViewSet,
    MedicinePaymentViewSet,
    PatientPrescriptionView,
)

router = DefaultRouter()

router.register(
    "profiles",
    PharmacistProfileViewSet,
    basename="pharmacist-profile",
)
router.register(
    "medicine-categories",
    MedicineCategoryViewSet,
    basename="medicine-category",
)
router.register(
    "medicines",
    MedicineViewSet,
    basename="medicine",
)
router.register(
    "suppliers",
    SupplierViewSet,
    basename="supplier",
)
router.register(
    "inventory-batches",
    InventoryBatchViewSet,
    basename="inventory-batch",
)
router.register(
    "stock-movements",
    StockMovementViewSet,
    basename="stock-movement",
)
router.register(
    "medicine-payments",
    MedicinePaymentViewSet,
    basename="medicine-payment",
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "patient-prescriptions/",
        PatientPrescriptionView.as_view(),
        name="patient-prescriptions",
    ),
]