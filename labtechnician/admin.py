
from django.contrib import admin
from .models import LabTechnicianProfile, LabTest, LabOrder, LabResult


@admin.register(LabTechnicianProfile)
class LabTechnicianProfileAdmin(admin.ModelAdmin):
    exclude = ("employee_id",)


admin.site.register(LabTest)


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = ("lab_order_name", "status", "ordered_at")

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("id")

    @admin.display(description="Lab order")
    def lab_order_name(self, obj):
        ids = list(self.get_queryset_ids())
        number = ids.index(obj.pk) + 1
        return f"{obj.lab_test.name} - Order {number}"

    def get_queryset_ids(self):
        return list(
            LabOrder.objects.order_by("id").values_list("id", flat=True)
        )


admin.site.register(LabResult)
