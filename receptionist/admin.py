
from django.contrib import admin
from .models import (
    ReceptionistProfile,
    Patient,
    Appointment,
    DailyDoctorQueue,
    QueueToken,
    ConsultationPayment,
)


@admin.register(ReceptionistProfile)
class ReceptionistProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "user")
    readonly_fields = ("employee_id",)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "patient_number",
        "first_name",
        "last_name",
        "phone_number",
        "gender",
        "created_at",
    )

    search_fields = (
        "patient_number",
        "first_name",
        "last_name",
        "phone_number",
        "email",
    )

    list_filter = ("gender", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("patient_number", "created_at")


admin.site.register(Appointment)
admin.site.register(DailyDoctorQueue)
admin.site.register(QueueToken)
admin.site.register(ConsultationPayment)
