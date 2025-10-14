from django.db import models
from user.models import UserAccount
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete, pre_save
from django.db.models import UniqueConstraint
from django.core.exceptions import ValidationError
from django.db.models import Sum
from decimal import Decimal
from django.db import transaction



class OrderLog(models.Model):
    ACTION_CHOICES = [
        ('Create', 'Create'),
        ('Update', 'Update'),
        ('Delete', 'Delete'),
    ]
    
    user = models.CharField(max_length=255, default="User", null=True, blank=True)
    action = models.CharField(max_length=100, choices=ACTION_CHOICES, null=True, blank=True)
    model_name = models.CharField(max_length=50, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)  # ID of the object affected
    timestamp = models.DateTimeField(auto_now_add=True)
    customer_info = models.CharField(max_length=255, default="Customer", null=True, blank=True)
    product_name = models.CharField(max_length=255, default="Product", null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    changes_on_update = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.action} - {self.model_name} ({self.object_id}) at {self.timestamp}"

class Category(models.Model):
    name = models.CharField(max_length=100, default='', unique=True)
    user = models.CharField(max_length=255, default="User", null=True, blank=True)

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=200, blank=True, null=True)
    contact_info = models.CharField(max_length=50, null=True, blank=True)
    tin_number = models.CharField(max_length=50, null=True, blank=True)
    user = models.CharField(max_length=255, default="User", null=True, blank=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200, blank=False, null=False)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    package = models.IntegerField(null=True, blank=True)
    piece = models.IntegerField(null=True, blank=True)
    buying_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=255, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField(null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    color_code = models.CharField(max_length=255, null=True, blank=True)
    receipt_no = models.IntegerField(null=True, blank=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    user = models.CharField(max_length=255, default="User", null=True, blank=True)

    def __str__(self):
        return self.name

class CustomerInfo(models.Model):
    name = models.CharField(max_length=255, default="Customer", null=True, blank=True)
    phone = models.CharField(max_length=255, null=True, blank=True)
    tin_number = models.CharField(max_length=255, null=True, blank=True)
    vat_number = models.CharField(max_length=255, null=True, blank=True)
    fs_number = models.CharField(max_length=255, null=True, blank=True)
    zone = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    sub_city = models.CharField(max_length=255, null=True, blank=True)
    user = models.CharField(max_length=255, default="User", null=True, blank=True)

    def __str__(self):
        return self.name

class CompanyInfo(models.Model):
    en_name = models.CharField(max_length=255, default="Company", null=True, blank=True)
    am_name = models.CharField(max_length=255, default="Company", null=True, blank=True)
    owner_en_name = models.CharField(max_length=255, default="Mubarek", null=True, blank=True)
    owner_am_name = models.CharField(max_length=255, default="Company", null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone1 = models.CharField(max_length=255, null=True, blank=True)
    phone2 = models.CharField(max_length=255, null=True, blank=True)
    bank_accounts = models.JSONField(default=dict, null=True, blank=True)
    tin_number = models.CharField(max_length=255, null=True, blank=True)
    vat_number = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    region = models.CharField(max_length=255, null=True, blank=True)
    zone = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    sub_city = models.CharField(max_length=255, null=True, blank=True)
    logo = models.ImageField(upload_to='company/', null=True, blank=True)
    user = models.CharField(max_length=255, default="User", null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['en_name', 'am_name', 'tin_number'], name='unique_company_fields')
        ]

    def __str__(self):
        return self.en_name

class Order(models.Model):
    ACTION_CHOICES = [
        ('Receipt', 'Receipt'),
        ('No Receipt', 'No Receipt')
    ]

    PAYMENT_STATUS=[
        ('Paid','Paid'),
        ('Unpaid','Unpaid'),
        ('Pending','Pending')
    ]

    customer = models.ForeignKey(CustomerInfo, on_delete=models.SET_NULL, null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=100, choices=(('Cancelled', 'Cancelled'), ('Pending', 'Pending'), ('Done', 'Done')), default="Done", null=True, blank=True)
    receipt = models.CharField(max_length=255, choices=ACTION_CHOICES, default="No Receipt", null=True, blank=True)
    receipt_id = models.CharField(max_length=255, null=True, blank=True)
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    vat = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS, default='Paid')
    paid_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, null=True, blank=True)
    unpaid_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    user = models.CharField(max_length=255, default="User", null=True, blank=True)
    user_email = models.CharField(max_length=255, default="User@gmail.com", null=True, blank=True)
    user_role = models.CharField(max_length=255, default="Salesman", null=True, blank=True)
    item_pending = models.PositiveIntegerField(null=True, blank=True)

    def str(self):
        return self.customer
    
    # @property
    def is_empty(self):
        return not self.items.exists() 

    def get_sub_total_price(self):
        """Calculate the total price of the entire order."""
        return sum(item.get_price() for item in self.items.all())
    
    def check_and_delete_if_no_items(self):
        if not self.items.exists():
            self.delete()

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    package = models.PositiveIntegerField(null=True, blank=True)
    unit = models.CharField(max_length=255, default="Pcs", null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    item_receipt = models.CharField(max_length=255, default="No Receipt", null=True, blank=True)
    status = models.CharField(max_length=100, choices=(('Cancelled', 'Cancelled'), ('Pending', 'Pending'), ('Done', 'Done')), default="Done", null=True, blank=True)

    def str(self):
        return self.product
    
    def get_price(self):
        """Calculate the total price of this item."""
        return self.price  # Now it returns the stored price
    
    def get_cost(self):
        """Calculate the total price of this item."""
        if self.product.buying_price is not None:
            if self.package is not None and self.product.piece is not None:
                cost = self.product.buying_price * (self.package * self.product.piece)
            elif self.quantity is not None:
                cost = self.product.buying_price * self.quantity
            return cost
        else:
            # If buying_price is None, return 0 or handle as needed
            return Decimal('0.00')
        
    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.check_and_delete_if_no_items()

class Report(models.Model):
    user = models.CharField(max_length=50, default="user", blank=True, null=True)
    customer_name = models.CharField(max_length=255, default="Customer", null=True, blank=True)
    customer_phone = models.CharField(max_length=255, default="Customer", null=True, blank=True)
    customer_tin_number = models.CharField(max_length=255, default="Customer", null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True)
    order_id = models.IntegerField(null=True, blank=True)
    item_receipt = models.CharField(max_length=255, default="No Receipt", null=True, blank=True)
    product_name = models.CharField(max_length=255, default="Product", null=True, blank=True)
    unit = models.CharField(max_length=255, default="Pcs", null=True, blank=True)
    product_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    quantity = models.IntegerField()
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    vat = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=50, default='Paid', null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  

    def __str__(self):
        return self.user

class ExpenseTypes(models.Model):
    name = models.CharField(max_length=100)
    user = models.CharField(max_length=255, default="User", null=True, blank=True)
    
    def __str__(self):
        return self.name

class OtherExpenses(models.Model):
    expense_type = models.ForeignKey(ExpenseTypes, on_delete=models.SET_NULL, blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.CharField(max_length=255, default="User", null=True, blank=True)

    def __str__(self):
        return self.name



class PurchaseSupplier(models.Model):
    status = (
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
        ('Pending', 'Pending')
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=50, choices=status, default='Pending')
    paid_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, null=True, blank=True)
    unpaid_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, null=True, blank=True)
    user = models.CharField(max_length=255, default="User", null=True, blank=True)

    def __str__(self):
        return f"{self.user}"

class PurchaseExpense(models.Model):
    status=(
        ('Paid','Paid'),
        ('Unpaid','Unpaid'),
        ('Pending','Pending')
    )
    purchase_date = models.DateTimeField(auto_now_add=True)
    supplier = models.CharField(max_length=255, null=True, blank=True)
    total = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=50, choices=status, default='Pending')
    paid_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, null=True, blank=True)
    unpaid_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, null=True, blank=True)
    user = models.CharField(max_length=255, default="User", null=True, blank=True)
    supplier_level = models.ForeignKey(PurchaseSupplier, related_name='expenses', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user}"

class PurchaseProduct(models.Model):
    product = models.CharField(max_length=255, default="Product", null=True, blank=True)
    unit = models.CharField(max_length=255, default="Pcs", null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    expense = models.ForeignKey(PurchaseExpense, related_name='products', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.description} - {self.total_price}"



# New Performa
class PerformaCustomer(models.Model):
    customer = models.ForeignKey(CustomerInfo, on_delete=models.SET_NULL, blank=True, null=True)
    user = models.CharField(max_length=255, default="User", null=True, blank=True)

    def __str__(self):
        return f"{self.user}"

class PerformaPerforma(models.Model):
    ACTION_CHOICES = [
        ('Receipt', 'Receipt'),
        ('No Receipt', 'No Receipt')
    ]
    customer = models.CharField(max_length=255, null=True, blank=True)
    issued_date = models.DateTimeField(auto_now_add=True)
    receipt = models.CharField(max_length=255, choices=ACTION_CHOICES, default="No Receipt", null=True, blank=True)
    sub_total = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    vat = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    user = models.CharField(max_length=255, default="User", null=True, blank=True)
    customer_level = models.ForeignKey(PerformaCustomer, related_name='performas', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user}"

class PerformaProduct(models.Model):
    product = models.CharField(max_length=255, default="Product", null=True, blank=True)
    unit = models.CharField(max_length=255, default="Pcs", null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    performa = models.ForeignKey(PerformaPerforma, related_name='products', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.description} - {self.total_price}"






class SupplierPaymentLog(models.Model):
    supplier = models.ForeignKey(PurchaseSupplier, on_delete=models.SET_NULL, related_name='logs', null=True, blank=True)
    change_type = models.CharField(max_length=255)
    field_name = models.CharField(max_length=100)
    old_value = models.CharField(max_length=255, null=True, blank=True)
    new_value = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.CharField(max_length=255, null=True, blank=True)

class ExpensePaymentLog(models.Model):
    expense = models.ForeignKey(PurchaseExpense, on_delete=models.SET_NULL, related_name='logs', null=True, blank=True)
    supplier = models.CharField(max_length=255, null=True, blank=True)
    change_type = models.CharField(max_length=255)
    field_name = models.CharField(max_length=100)
    old_value = models.CharField(max_length=255, null=True, blank=True)
    new_value = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.CharField(max_length=255, null=True, blank=True)

class OrderPaymentLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, related_name='logs', null=True, blank=True)
    customer = models.CharField(max_length=255, null=True, blank=True, default="Customer")
    change_type = models.CharField(max_length=255)
    field_name = models.CharField(max_length=100)
    old_value = models.CharField(max_length=255, null=True, blank=True)
    new_value = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.CharField(max_length=255, null=True, blank=True)





@receiver(post_save, sender=PurchaseProduct)
def update_expense_total_on_delete(sender, instance, **kwargs):
    expense = instance.expense
    if not expense:
        return

    def update_expense_totals():
        total = expense.products.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
        expense.total = total
        expense.unpaid_amount = expense.total - expense.paid_amount
        expense.save(update_fields=['total', 'unpaid_amount'])

    transaction.on_commit(update_expense_totals)

@receiver(pre_save, sender=OrderItem)
def set_order_item_price(sender, instance, **kwargs):
    """Calculate price before saving the OrderItem instance."""
    instance.price = instance.get_price()

@receiver(pre_save, sender=OrderItem)
def set_order_item_cost(sender, instance, **kwargs):
    """Calculate price before saving the OrderItem instance."""
    instance.cost = instance.get_cost()

@receiver([post_save, post_delete], sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    """Update total amount in Order when an OrderItem is added, updated, or deleted."""
    order = instance.order
    order.sub_total = order.get_sub_total_price()
    if order.receipt == 'Receipt':
        order.vat = order.sub_total * Decimal('0.15')
    else:
        order.vat = 0
    order.total_amount = order.sub_total + order.vat
    if order.payment_status == 'Paid':
        order.paid_amount = order.total_amount
    else:
        order.unpaid_amount = order.total_amount - order.paid_amount
    order.save()

@receiver([post_save, post_delete], sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    """Update total amount in Order when an OrderItem is added, updated, or deleted."""
    order = instance.order
    order.sub_total = order.get_sub_total_price()
    # Update VAT and total_amount here as well:
    if order.receipt == 'Receipt':
        order.vat = order.sub_total * Decimal('0.15')
    else:
        order.vat = 0
    order.total_amount = order.sub_total + order.vat
    if order.payment_status == 'Paid':
        order.paid_amount = order.total_amount
    elif order.payment_status == 'Pending':
        order.unpaid_amount = order.total_amount - order.paid_amount
    order.save()

@receiver(post_save, sender=Order)
def update_order_total_on_order_change(sender, instance, **kwargs):
    total = sum(item.price for item in instance.items.all())
    instance.sub_total = total
    if instance.receipt == 'Receipt':
        instance.vat = total * Decimal('0.15')  # Assuming a VAT rate of 15%
    else:
        instance.vat = 0
    instance.total_amount = total + instance.vat

@receiver(post_save, sender=OrderItem)
def update_order_status_if_all_items_status_cancelled(sender, instance, **kwargs):
    # Check if the associated order has no items with status 'Done'
    order = instance.order
    items = order.items.all()
    if items.exists() and items.filter(status='Cancelled').count() == items.count():
        order.status = 'Cancelled'
        order.save()

@receiver(post_save, sender=Order)
def update_order_items_status_on_order_update(sender, instance, **kwargs):
    """
    When an order is updated, update all related OrderItem statuses to 'Cancelled'
    if the order's status is set to 'Cancelled'.
    Also, restock products when an order item is cancelled.
    """

    if getattr(instance, '_updating', False):
        return  # Prevent recursion
    
    if instance.status == 'Cancelled':  # Check if the order is cancelled
        items_data = instance.items.all()  # Retrieve all related OrderItem instances
        instance.sub_total = 0  # Reset sub_total to 0 when cancelling
        instance.vat = 0  # Reset VAT to 0 when cancelling
        instance.total_amount = 0  # Reset total_amount to 0 when cancelling
        instance.paid_amount = 0  # Reset paid_amount to 0 when cancelling
        instance.unpaid_amount = 0  # Reset unpaid_amount to 0 when cancelling
        instance.payment_status = 'Unpaid'  # Reset payment_status to 'Unpaid' when cancelling
        # instance.save()  # Save the updated order
        
        instance._updating = True  # Set flag
        instance.save(update_fields=['sub_total', 'vat', 'total_amount', 'paid_amount', 'unpaid_amount', 'payment_status'])
        instance._updating = False  # Unset flag

        items_to_update = []  # List to collect OrderItems for bulk update

        for item_data in items_data:
            product = item_data.product  # Access related product
            receipt = item_data.item_receipt  # Access receipt type
            quantity = item_data.quantity  # Access quantity
            package = item_data.package  # Access package


            if item_data.status != 'Cancelled':  # Check if item is not already cancelled
                product.stock += item_data.quantity  # Restock the product
                item_data.quantity = 0 
                item_data.price = 0
                item_data.unit_price = 0 
                item_data.cost = 0
                item_data.status = 'Cancelled'  # Mark item as cancelled
                if product.package is not None and package is not None:
                    product.package += package
                    item_data.package = 0
                if receipt == "Receipt":
                    if product.receipt_no is not None:
                        product.receipt_no += quantity
                items_to_update.append(item_data)  # Collect for bulk update

                # Save the updated product and order item
                product.save()  # Save the updated product
                # item_data.save()  # Save the updated order item but it causes the multiple save issue

        # Bulk update all OrderItems at once
        OrderItem.objects.bulk_update(items_to_update, ['quantity', 'status', 'price', 'unit_price', 'cost', 'package'])

@receiver([post_save, post_delete], sender=OrderItem)
def update_order_item_pending_count(sender, instance, **kwargs):
    order = instance.order
    items = order.items.all()
    pending_count = items.filter(status='Pending').count()
    done_exists = items.filter(status='Done').exists()

    if items.count() == 1 and items.first().status == 'Pending':
        order.item_pending = 0
        order.status = "Pending"
    elif items.count() > 1:
        if done_exists:
            order.item_pending = pending_count
        elif not done_exists and items.exists() and items.filter(status='Pending').count() == items.count():
            order.item_pending = 0
            order.status = "Pending"
    else:
        order.item_pending = 0  # No items at all

    order.save(update_fields=['item_pending', 'status'])

@receiver(post_save, sender=PurchaseExpense)
def update_purchase_supplier_total_amount(sender, instance, **kwargs):
    supplier = instance.supplier_level
    if not supplier:
        return

    def update_supplier_totals():
        supplier.total_amount = supplier.expenses.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
        supplier.paid_amount = supplier.expenses.aggregate(Sum('paid_amount'))['paid_amount__sum'] or Decimal('0.00')
        supplier.unpaid_amount = supplier.expenses.aggregate(Sum('unpaid_amount'))['unpaid_amount__sum'] or Decimal('0.00')
        supplier.save(update_fields=['total_amount', 'paid_amount', 'unpaid_amount'])

    transaction.on_commit(update_supplier_totals)

@receiver(post_save, sender=PurchaseExpense)
def set_supplier_paid_if_all_expenses_paid(sender, instance, **kwargs):
    supplier = instance.supplier_level
    if supplier:
        # Check if all related expenses are paid
        all_paid = not supplier.expenses.exclude(payment_status='Paid').exists()
        if all_paid and supplier.payment_status != 'Paid':
            supplier.payment_status = 'Paid'
            supplier.save(update_fields=['payment_status'])

@receiver(post_save, sender=PurchaseSupplier)
def set_expenses_paid_if_supplier_paid(sender, instance, **kwargs):
    # print("Supplier post_save signal fired!", instance.pk, instance.payment_status)
    if instance.payment_status == 'Paid':
        instance.expenses.update(
            payment_status='Paid',
            paid_amount=models.F('total'),
            unpaid_amount=0
    )

@receiver(post_save, sender=PerformaProduct)
def update_performa_total_on_update(sender, instance, **kwargs):
    performa = instance.performa
    if not performa:
        return

    def update_performa_totals():
        total = performa.products.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
        performa.sub_total = total
        if performa.receipt == 'Receipt':
            performa.vat = performa.sub_total * Decimal('0.15')
        else:
            performa.vat = 0
        performa.total = performa.sub_total + performa.vat
        performa.save(update_fields=['sub_total', 'vat', 'total'])

    transaction.on_commit(update_performa_totals)

@receiver(post_delete, sender=PerformaProduct)
def update_performa_total_on_delete(sender, instance, **kwargs):
    try:
        performa = instance.performa
    except PerformaPerforma.DoesNotExist:
        # If the Performa is already deleted, we don't need to update anything
        return
    if not performa.products.exists():
        performa.sub_total = 0
        performa.vat = 0
        performa.total = 0
        performa.save(update_fields=['sub_total', 'vat', 'total'])
    else:
        performa.sub_total = performa.products.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
        if performa.receipt == 'Receipt':
            performa.vat = performa.sub_total * Decimal('0.15')
        else:
            performa.vat = 0
        performa.total = performa.sub_total + performa.vat
        performa.save(update_fields=['sub_total', 'vat', 'total'])
    
