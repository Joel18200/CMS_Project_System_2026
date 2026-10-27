from django.contrib import admin
from .models import ReceptionistProfile, Patient, Appointment, DailyDoctorQueue, QueueToken, ConsultationPayment

admin.site.register(ReceptionistProfile)
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("patient_number",)
    readonly_fields = ("patient_number",)
admin.site.register(Appointment)
admin.site.register(DailyDoctorQueue)
admin.site.register(QueueToken)
admin.site.register(ConsultationPayment)