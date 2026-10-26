from django.contrib import admin
from .models import PharmacistProfile, MedicineCategory, Medicine, Supplier, InventoryBatch, StockMovement, MedicinePayment

admin.site.register(PharmacistProfile)
admin.site.register(MedicineCategory)
admin.site.register(Medicine)
admin.site.register(Supplier)
admin.site.register(InventoryBatch)
admin.site.register(StockMovement)
admin.site.register(MedicinePayment)