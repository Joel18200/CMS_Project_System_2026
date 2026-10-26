from django.contrib import admin
from .models import LabTechnicianProfile, LabTest, LabOrder, LabResult

admin.site.register(LabTechnicianProfile)
admin.site.register(LabTest)
admin.site.register(LabOrder)
admin.site.register(LabResult)