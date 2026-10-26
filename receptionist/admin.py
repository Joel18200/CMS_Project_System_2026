from django.contrib import admin
from .models import ReceptionistProfile, Patient, Appointment, DailyDoctorQueue, QueueToken, ConsultationPayment

admin.site.register(ReceptionistProfile)
admin.site.register(Patient)
admin.site.register(Appointment)
admin.site.register(DailyDoctorQueue)
admin.site.register(QueueToken)
admin.site.register(ConsultationPayment)