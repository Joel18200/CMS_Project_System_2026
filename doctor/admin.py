from django.contrib import admin
from .models import DoctorProfile, DoctorSchedule, Consultation, ClinicalNote, Prescription, PrescriptionItem, SurgeryAdvice

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "employee_id",
        "user",
        "specialization",
        "registration_number",
    )
    readonly_fields = ("employee_id",)
admin.site.register(DoctorSchedule)
admin.site.register(Consultation)
admin.site.register(ClinicalNote)
admin.site.register(Prescription)
admin.site.register(PrescriptionItem)
admin.site.register(SurgeryAdvice)

