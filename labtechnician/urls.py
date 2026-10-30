
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register(
    "profiles",
    views.LabTechnicianProfileViewSet,
    basename="labtechnicianprofile",
)

router.register(
    "tests",
    views.LabTestViewSet,
    basename="labtest",
)

router.register(
    "orders",
    views.LabOrderViewSet,
    basename="laborder",
)

router.register(
    "results",
    views.LabResultViewSet,
    basename="labresult",
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "today-orders/",
        views.today_lab_orders,
        name="today_lab_orders",
    ),
]
