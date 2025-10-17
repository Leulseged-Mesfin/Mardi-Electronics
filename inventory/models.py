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
    specification = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    package = models.IntegerField(null=True, blank=True)
    piece = models.IntegerField(null=True, blank=True)
    buying_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=255, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField(null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
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
    
    VAT_TYPE=[
            ('Inclusive','Inclusive'),
            ('Exclusive','Exclusive'),
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
    vat_type = models.CharField(max_length=50, choices=VAT_TYPE, default='Inclusive')
    number_of_items = models.IntegerField(null=True, blank=True)
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


class OrderPaymentLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, related_name='logs', null=True, blank=True)
    customer = models.CharField(max_length=255, null=True, blank=True, default="Customer")
    change_type = models.CharField(max_length=255)
    field_name = models.CharField(max_length=100)
    old_value = models.CharField(max_length=255, null=True, blank=True)
    new_value = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.CharField(max_length=255, null=True, blank=True)




@receiver(pre_save, sender=OrderItem)
def set_order_item_price(sender, instance, **kwargs):
    """Calculate price before saving the OrderItem instance."""
    instance.price = instance.get_price()

@receiver(pre_save, sender=OrderItem)
def set_order_item_cost(sender, instance, **kwargs):
    """Calculate price before saving the OrderItem instance."""
    instance.cost = instance.get_cost()


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


@receiver([post_save, post_delete], sender=OrderItem)
def update_order_totals(sender, instance, **kwargs):
    order = instance.order
    order.sub_total = order.get_sub_total_price()

    # Handle VAT and total_amount based on receipt type
    if order.receipt == 'Receipt':
        if order.vat_type == 'Exclusive':
            order.vat = order.sub_total * Decimal('0.15')
            order.total_amount = order.sub_total + order.vat
        elif order.vat_type == 'Inclusive':
            order.total_amount = order.get_sub_total_price()  # Total including VAT
            order.sub_total = order.total_amount / (1 + Decimal('0.15'))  # Pre-VAT amount
            order.vat = order.total_amount - order.sub_total  # VAT amount
        else:
            order.vat = 0
            order.total_amount = order.sub_total
    else:
        order.vat = 0
        order.total_amount = order.sub_total

    # Handle payment status
    if order.payment_status == 'Paid':
        order.paid_amount = order.total_amount
    else:
        order.unpaid_amount = order.total_amount - order.paid_amount

    # Save only once, with update_fields to avoid unnecessary recalculations
    order.save(update_fields=['sub_total', 'vat', 'total_amount', 'paid_amount', 'unpaid_amount'])


@receiver([post_save, post_delete], sender=OrderItem)
def update_order_item_count(sender, instance, **kwargs):
    order = instance.order
    items = order.items.all()
    items_count = items.all().count()
    order.number_of_items = items_count
    order.save(update_fields=['number_of_items'])

