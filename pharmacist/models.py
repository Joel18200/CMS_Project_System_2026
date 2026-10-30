from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.validators import MinValueValidator


class PharmacistProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pharmacist_profile",
    )
    employee_id = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.employee_id


class MedicineCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Medicine(models.Model):
    name = models.CharField(max_length=150)
    category = models.ForeignKey(
        MedicineCategory,
        on_delete=models.PROTECT,
        related_name="medicines",
    )
    strength = models.CharField(max_length=50)
    dosage_form = models.CharField(max_length=50)
    unit_of_measure = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "strength", "dosage_form"],
                name="unique_medicine_variant",
            )
        ]

    def __str__(self):
        return f"{self.name} {self.strength}"


class Supplier(models.Model):
    name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class InventoryBatch(models.Model):
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="batches",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="supplied_batches",
    )
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField()
    purchase_price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    selling_price_per_unit = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=0,
    validators=[MinValueValidator(0)],
    )

    mrp_per_unit = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=0,
    validators=[MinValueValidator(0)],
    )

    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["medicine", "batch_number"],
                name="unique_batch_per_medicine",
            )
        ]

    def __str__(self):
        return f"{self.medicine.name} - Batch {self.batch_number}"

    @property
    def available_quantity(self):
        return sum(
            self.stock_movements.values_list("quantity_change", flat=True)
        )


class StockMovement(models.Model):

    class MovementType(models.TextChoices):
        STOCK_RECEIVED = "STOCK_RECEIVED", "Stock Received"
        DISPENSED = "DISPENSED", "Dispensed"
        RETURNED = "RETURNED", "Returned"
        DAMAGED = "DAMAGED", "Damaged"
        EXPIRED = "EXPIRED", "Expired"
        ADJUSTED = "ADJUSTED", "Adjusted"

    inventory_batch = models.ForeignKey(
        InventoryBatch,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    prescription_item = models.ForeignKey(
        "doctor.PrescriptionItem",
        on_delete=models.PROTECT,
        related_name="stock_movements",
        null=True,
        blank=True,
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
    )
    quantity_change = models.IntegerField()
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(quantity_change=0),
                name="stock_movement_nonzero_quantity",
            )
        ]

    def __str__(self):
        return (
            f"{self.movement_type} - "
            f"Batch {self.inventory_batch_id}: "
            f"{self.quantity_change}"
        )


class MedicinePayment(models.Model):

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        CARD = "CARD", "Card"
        UPI = "UPI", "UPI"
        ONLINE = "ONLINE", "Online"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESSFUL = "SUCCESSFUL", "Successful"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    prescription = models.OneToOneField(
        "doctor.Prescription",
        on_delete=models.PROTECT,
        related_name="medicine_payment",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices,
    )
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medicine_payments_received",
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"Prescription {self.prescription_id} - "
            f"{self.payment_status}"
        )


class MedicineBill(models.Model):
    bill_number = models.CharField(max_length=30, unique=True)

    prescription = models.ForeignKey(
        "doctor.Prescription",
        on_delete=models.PROTECT,
        related_name="medicine_bills",
    )

    payment = models.ForeignKey(
        MedicinePayment,
        on_delete=models.PROTECT,
        related_name="bills",
    )

    bill_date = models.DateTimeField(auto_now_add=True)

    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    dispensed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medicine_bills_dispensed",
    )

    def __str__(self):
        return self.bill_number


class MedicineBillItem(models.Model):
    bill = models.ForeignKey(
        MedicineBill,
        on_delete=models.CASCADE,
        related_name="items",
    )

    prescription_item = models.ForeignKey(
        "doctor.PrescriptionItem",
        on_delete=models.PROTECT,
    )

    inventory_batch = models.ForeignKey(
        InventoryBatch,
        on_delete=models.PROTECT,
    )

    quantity = models.PositiveIntegerField()

    rate = models.DecimalField(
        max_digits=10, decimal_places=2
    )

    mrp = models.DecimalField(
        max_digits=10, decimal_places=2
    )

    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    gst_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )

    cgst_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    sgst_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    net_amount = models.DecimalField(
        max_digits=10, decimal_places=2
    )

    stock_movement = models.OneToOneField(
        "StockMovement",
        on_delete=models.PROTECT,
        related_name="bill_item",
    )

    def __str__(self):
        return f"{self.bill.bill_number} - {self.prescription_item.medicine}"