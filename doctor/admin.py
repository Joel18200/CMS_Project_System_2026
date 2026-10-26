from django.contrib import admin
from .models import DoctorProfile, DoctorSchedule, Consultation, ClinicalNote, Prescription, PrescriptionItem, SurgeryAdvice

admin.site.register(DoctorProfile)
admin.site.register(DoctorSchedule)
admin.site.register(Consultation)
admin.site.register(ClinicalNote)
admin.site.register(Prescription)
admin.site.register(PrescriptionItem)
admin.site.register(SurgeryAdvice)

