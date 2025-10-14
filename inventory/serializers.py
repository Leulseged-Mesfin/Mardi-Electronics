from rest_framework import serializers
from .models import (
    Product, Supplier, Order, OrderItem, CustomerInfo,  
    Category, CompanyInfo, OrderLog, Report, ExpenseTypes, 
    OtherExpenses, PurchaseSupplier, 
    PurchaseExpense, PurchaseProduct, SupplierPaymentLog, 
    ExpensePaymentLog, OrderPaymentLog, PerformaCustomer, 
    PerformaPerforma, PerformaProduct
)

from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import UniqueConstraint
from user.models import UserAccount
from user.serializers import UserSerializer
from django.utils import timezone
from .utils import create_order_log, create_order_report
from decimal import Decimal
from django.db.models import Q, Sum, Count
from rest_framework.response import Response
from rest_framework import status, permissions
from .utils import update_payment_status_on_new_expense_or_product


class CategorySerializer(serializers.ModelSerializer):
    name = serializers.CharField(validators=[])  # Disable default unique validator

    class Meta:
        model = Category
        fields = '__all__'
    
    def validate_name(self, value):
        # Exclude the current instance when updating
        qs = Category.objects.filter(name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A category with this name already exists.")
        return value
    

    def create(self, validated_data, user=None):
        if user:
            validated_data['user'] = user.name
        return super().create(validated_data)
        
class SupplierSerializer(serializers.ModelSerializer):

    class Meta:
        model = Supplier
        fields = '__all__'
    
    def create(self, validated_data, user=None):
        # Add the user to the validated_data if provided
        if user:
            validated_data['user'] = user.name
        return super().create(validated_data)

class ProductGetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'category_name', 'description', 'package', 'piece', 'unit', 'buying_price', 'selling_price', 'receipt_no', 'color_code', 'stock', 'supplier_name', 'image', 'user']
        constraints = [
            UniqueConstraint(fields=['name', 'category_name', 'color_code'], name='unique_product_category_color_code')
        ]

class ProductPostSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = '__all__'
        constraints = [
            UniqueConstraint(fields=['name', 'category', 'color_code'], name='unique_product_category_color_code')
        ]
    
    def validate(self, attrs):
        name = attrs.get('name')
        category = attrs.get('category')
        color_code = attrs.get('color_code')
        if Product.objects.filter(name=name, category=category, color_code=color_code).exists():
            raise serializers.ValidationError(
                {"error": "A product with this name, category and color code already exists."}
            )
        return super().validate(attrs)
    
    def create(self, validated_data, user=None):
        # Add the user to the validated_data if provided
        package = validated_data.get('package', None)
        piece = validated_data.get('piece', None)
        stock = validated_data.get('stock', None)

        if package is not None and piece is not None:
            stock = package * piece
            if stock < 0:
                  raise serializers.ValidationError({"error": "stock can't be negative"})
            validated_data['stock'] = stock
        if stock is not None:
            if stock < 0:
                  raise serializers.ValidationError({"error": "stock can't be negative"})
            validated_data['stock'] = stock


        if user:
            validated_data['user'] = user.name

        return super().create(validated_data)


    def update(self, instance, validated_data):
        update_package = validated_data.pop('package', None) # Get the number of boxes to add
        piece = validated_data.pop('piece', instance.piece) # Get the number of strips to add
        update_stocks = validated_data.pop('stock', None)  # Get the
        
        validated_data['piece'] = piece

        if update_package == instance.package:
            update_package = None

    
       # Calculate stock if boxes are provided
        if update_package is not None:
            # Calculate stock based on strips and boxes
            # piece = instance.piece  # Get the current strips per box
            if instance.package is not None:
                update_package = instance.package + update_package  # Update boxes per carton
                stock_quantity = piece * update_package
                module_stock = instance.stock % piece
                stock = stock_quantity + module_stock
                validated_data['package'] = stock // piece
                if stock < 0:
                  raise serializers.ValidationError({"error": "stock can't be negative"})
                validated_data['stock'] = stock  # Update the stock in validated_data
            else:
                stock_quantity = piece * update_package
                module_stock = instance.stock % piece
                stock = stock_quantity + module_stock
                validated_data['package'] = stock // piece
                if stock < 0:
                  raise serializers.ValidationError({"error": "stock can't be negative"})
                validated_data['stock'] = stock  # Update the stock in validated_data
           
        elif update_stocks is not None and instance.stock is not None:
            # If update_stocks is provided, update the stock directly
            if instance.piece is not None and instance.package is not None:
                stock = instance.stock + update_stocks
                remaining_package = stock // instance.piece
                validated_data['package'] = remaining_package  # Update boxes per carton based on remaining stock
                if stock < 0:
                  raise serializers.ValidationError({"error": "stock can't be negative"})
                validated_data['stock'] = stock
            else:
               stock = instance.stock + update_stocks
               if stock < 0:
                  raise serializers.ValidationError({"error": "stock can't be negative"})
               validated_data['stock'] = stock

        else:
            validated_data['stock'] = update_stocks if update_stocks is not None else instance.stock  # Use provided stock or keep existing        

        return super().update(instance, validated_data)


class CustomerInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerInfo
        fields = '__all__'
    
    def create(self, validated_data, user=None):
        # Add the user to the validated_data if provided
        if user:
            validated_data['user'] = user.name
        return super().create(validated_data)

class CompanyInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyInfo
        fields = '__all__'
        constraints = [
            UniqueConstraint(fields=['en_name', 'am_name', 'tin_number'], name='unique_company_fields')
        ]
    
    def create(self, validated_data, user=None):
        # Add the user to the validated_data if provided
        if user:
            validated_data['user'] = user.name
        return super().create(validated_data)


class OrderItemSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)  # Read-only
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.SerializerMethodField()
    id = serializers.IntegerField(required=False)
    quantity = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'product', 'product_price', 'product_name', 'item_receipt', 'package', 'unit', 'quantity', 'unit_price', 'price', 'status']
        extra_kwargs = {
            'order': {'required': False},  # Make 'order' optional in the request
            'price': {'read_only': True}, # Make 'price' read-only if calculated
            'quantity': {'required': False, 'allow_null': True},
        }
    
    def get_product_price(self, obj):
        if obj.unit_price > 0:
            return str(obj.unit_price)
        elif obj.unit_price == 0 or obj.unit_price is None:
            if obj.product and obj.product.selling_price is not None:
                return str(obj.product.selling_price)
            else:
                return "0"
        else:
            return "0"
        

    def update(self, instance, validated_data):
        user = self.context['request'].user
        user_role = user.role
        user_name = user.name
        # Update order fields directly
        new_quantity = validated_data.get('quantity')
        new_status = validated_data.get('status')
        new_package = validated_data.get('package')
        new_unit_price = validated_data.get('unit_price')
        product = instance.product  # Access the product from the existing order item
        quantity = instance.quantity
        receipt = instance.order.receipt  # Access the receipt from the order
        package = instance.package
        unit_price = instance.unit_price
        piece = product.piece



        # If a salesman tries to cancel, set to Pending and raise error
        if new_status == 'Cancelled' and user_role == 'Salesman' or new_status == 'Cancelled' and user_role == 'Sales Manager':
            instance.status = 'Pending'
            instance.save()

            create_order_log(
                user=user_name,
                action="Request Cancel",
                model_name="OrderItem",
                object_id=instance.id,
                customer_info=instance.order.customer,
                product_name=instance.product.name,
                quantity=instance.quantity,
                price=instance.price,
                changes_on_update="Salesman requested cancellation"
            )

            raise serializers.ValidationError({
                "error": "You cannot cancel orders directly. Your cancellation request is now pending manager/admin approval."
            })


        if new_quantity and instance.status == 'Cancelled':
            raise serializers.ValidationError({
                "error": f"The order is already cancelled."
            })
        
        if new_package and instance.status == 'Cancelled':
            raise serializers.ValidationError({
                "error": f"The order is already cancelled."
            })


        if new_quantity and new_quantity <= 0:
            raise serializers.ValidationError({
                "error": f"Quantity must be greater than zero."
            })
        
        if new_package and new_package <= 0:
            raise serializers.ValidationError({
                "error": f"Package must be greater than zero."
            })
        
        if new_status:
            if new_status == 'Cancelled':
                product.stock += instance.quantity
                instance.quantity = 0
                instance.unit_price = 0
                instance.product_price = 0
                instance.price = 0
                instance.cost = 0
                instance.status = 'Cancelled' 
                if product.package is not None and package is not None:
                    product.package += package
                    instance.package = 0
                if receipt == "Receipt":
                    if product.receipt_no is not None:
                        product.receipt_no += quantity
                product.save()
                instance.save()
            elif new_status == 'Done':
                instance.status = 'Done' 
                instance.save()

        # updating if there is quantity
        if new_quantity and new_quantity > 0 and instance.status == 'Done':
            # Calculate the difference between new and existing quantity
            quantity_difference = new_quantity - quantity
            instance.quantity = new_quantity

            if product.stock >= quantity_difference:  # Ensure there is enough stock
                # Reduce stock by the order quantity_difference

                if receipt == "Receipt":
                    if package:
                        if product.package >= package:
                            product.package -= package
                            product.stock -= quantity_difference
                            if product.receipt_no is not None:
                                product.receipt_no -= quantity_difference
                            product.save()  # Save the product instance
                        elif product.package < package:
                            # raise ValidationError("The amount of package is insufficient.")
                            raise serializers.ValidationError({
                                "error": f"The amount of package is insufficient."
                            })
                            
                    elif package is None:
                        # Calculate the remaining stock and adjust the package count
                        remaining_stock = product.stock - quantity_difference
                        remaining_packages = remaining_stock // piece  # Calculate remaining packages
                        product.package = remaining_packages
                        product.stock = remaining_stock
                        if product.receipt_no is not None:
                            product.receipt_no -= quantity_difference
                        product.save()  # Save the product instance

                elif receipt == "No Receipt":
                    if package:
                        if product.package >= package:
                            product.package -= package
                            product.stock -= quantity_difference
                            product.save()  # Save the product instance
                        elif product.package < package:
                            raise serializers.ValidationError({
                                    "error": f"The amount of package is insufficient."
                                })
                    elif package is None:
                        # Calculate the remaining stock and adjust the package count
                        remaining_stock = product.stock - quantity_difference
                        remaining_packages = remaining_stock // piece  # Calculate remaining packages
                        product.package = remaining_packages
                        product.stock = remaining_stock
                        product.save()  # Save the product instance
                    
            else:
                raise serializers.ValidationError({
                        "error": f"Insufficient stock for {product.name}. Available stock is {product.stock}, but {quantity} was requested."
                    })
            # Update the instance's quantity
            instance.quantity = new_quantity

            # The total price without VAT
            if unit_price > 0 and new_unit_price is None:
                instance.price = unit_price * instance.quantity
            elif new_unit_price is not None:
                instance.unit_price = new_unit_price
                instance.price = new_unit_price * instance.quantity
            else:
                instance.price = product.selling_price * instance.quantity

        # updating if there is package
        if new_package and new_package > 0 and instance.status == 'Done' and piece is not None:
            # Calculate the difference between new and existing package
            package_difference = new_package - package
            print(f"package_difference: {package_difference}")
            package_quantity_difference = package_difference * piece
            print(f"package_quantity_difference: {package_quantity_difference}")
            print(f"product stock: {product.stock}")
            print(f"product package: {product.package}")
            print(f"product package calculated: {product.package - package_difference}")
            print(f"product stock calculated: {product.stock - package_quantity_difference}")
            instance.quantity = package_quantity_difference

            if product.stock >= package_quantity_difference:  # Ensure there is enough stock
                # Reduce stock by the order package_difference

                if receipt == "Receipt":
                    if package:
                        if product.package >= package_difference:
                            product.package -= package_difference
                            product.stock -= package_quantity_difference
                            if product.receipt_no is not None:
                                product.receipt_no -= package_quantity_difference
                            instance.package = new_package
                            instance.quantity = new_package * piece
                            product.save()  # Save the product instance
                        elif product.package < package_difference:
                            raise serializers.ValidationError({
                                "error": f"The amount of package is insufficient."
                            })    
                    elif package is None:
                        # Calculate the remaining stock and adjust the package count
                        remaining_stock = product.stock - package_quantity_difference
                        if piece:
                            remaining_packages = remaining_stock // piece  # Calculate remaining packages
                            product.package = remaining_packages
                        product.stock = remaining_stock
                        if product.receipt_no is not None:
                            product.receipt_no -= package_quantity_difference
                        product.save()  # Save the product instance

                elif receipt == "No Receipt":
                    if package:
                        if product.package >= package_difference:
                            product.package -= package_difference
                            product.stock -= package_quantity_difference
                            instance.package = new_package
                            instance.quantity = new_package * piece
                            product.save()  # Save the product instance
                        elif product.package < package_difference:
                            raise serializers.ValidationError({
                                "error": f"The amount of package is insufficient."
                            })
                    elif package is None:
                        # Calculate the remaining stock and adjust the package count
                        remaining_stock = product.stock - package_quantity_difference
                        remaining_packages = remaining_stock // piece  # Calculate remaining packages
                        product.package = remaining_packages
                        product.stock = remaining_stock
                        product.save()  # Save the product instance
                    
            else:
                raise serializers.ValidationError({
                        "error": f"Insufficient stock for {product.name}. Available stock is {product.stock}, but {quantity} was requested."
                    })
            # Update the instance's quantity
            # if new_quantity is not None:
            #     instance.quantity = new_quantity
            # elif new_package is not None:
            #     instance.package = new_package

            # The total price without VAT
            if unit_price > 0 and new_unit_price is None:
                instance.price = unit_price * instance.quantity
            elif new_unit_price is not None:
                instance.unit_price = new_unit_price
                instance.price = new_unit_price * instance.quantity
            else:
                instance.price = product.selling_price * instance.quantity


        instance.save()

        return instance

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_fs = serializers.CharField(source='customer.fs_number', read_only=True)
    

    class Meta:
        model = Order
        fields = ['id', 'customer', 'customer_name', 'customer_fs', 'status', 'receipt', 'receipt_id', 'order_date', 'sub_total', 'vat',  'total_amount', 'payment_status', 'paid_amount', 'unpaid_amount', 'items', 'user', 'user_email', 'user_role', 'item_pending']
        extra_kwargs = {
            'total_amount': {'required': False},
            'total_amount': {'read_only': True}, # Make 'total_amount' read-only
        }
    
    def create(self, validated_data, user=None):
        user = self.context["request"].user
        if user:
            validated_data['user'] = user.name
            validated_data['user_email'] = user.email
            validated_data['user_role'] = user.role

        
        receipt = validated_data['receipt']

        all_order = Order.objects.all().count()
        receipt_order = Order.objects.filter(receipt="Receipt").count()
        no_receipt_order = Order.objects.filter(receipt="No Receipt").count()
        if receipt == "Receipt":
            id = all_order - no_receipt_order
            id = str(id).zfill(4)
            validated_data['receipt_id'] = id
        else:
            validated_data['receipt_id'] = None



        payment_status = validated_data.get('payment_status', 'Paid')
        paid_amount = validated_data.get('paid_amount', 0)

        new_payment_status = payment_status
        new_paid_amount = paid_amount
        

        items_data = validated_data.pop('items')

        

        
        # If we get here, all validations passed - create the order
        with transaction.atomic():
            
            # First validate all items before creating anything
            for item_data in items_data:
                product = item_data['product']
                if product.stock is None:
                    raise serializers.ValidationError({
                        "error": f"Product {product.name} stock is not available."
                    })

            # Create the Order instance           
            order = Order.objects.create(**validated_data)

            # Create each OrderItem
            for item_data in items_data:
                # This will call OrderItemSerializer.validate() for each item
                product = item_data['product']
                quantity = item_data.get('quantity')
                receipt = order.receipt
                item_data['item_receipt'] = receipt
                package = item_data.get('package')
                unit_price = item_data.get('unit_price', product.selling_price)  # Default to product's selling price if not provided
                item_data['unit'] = item_data.get('unit', product.unit)
                
                piece = product.piece

                if receipt == "Receipt":
                    if package:
                        if product.package >= package:
                            product.package -= package
                            quantity = package * product.piece
                            item_data['quantity'] = quantity
                            if quantity >  product.stock:
                                raise serializers.ValidationError({
                                    "error": f"Insufficient stock for {product.name}. Available stock is {product.package}, but {quantity} was requested."
                                })
                            product.stock -= quantity
                            if product.receipt_no is not None:
                                product.receipt_no -= quantity
                            product.save()  # Save the product instance

                        elif product.package < package:
                            raise serializers.ValidationError({"error": f"Insufficient stock for {product.name}. Available stock is {product.stock}, but {quantity} was requested."})   
                    
                    elif package is None:
                        if quantity >  product.stock:
                            raise serializers.ValidationError({
                                "error": f"Insufficient stock for {product.name}. Available stock is {product.stock}, but {quantity} was requested."
                            })
                        # Calculate the remaining stock and adjust the package count
                        remaining_stock = product.stock - quantity
                        if product.piece is not None and product.package is not None:
                            # If piece and package are defined, calculate remaining packages
                            remaining_packages = remaining_stock // piece  # Calculate remaining packages
                            product.package = remaining_packages
                            product.stock = remaining_stock
                            product.save()
                            if product.receipt_no is not None:
                                # If receipt_no is defined, reduce it by the quantity
                                product.receipt_no -= quantity
                                product.save()  # Save the product instance
                        else:
                            product.stock -= quantity
                            product.save()  # Save the product instance  
                            if product.receipt_no is not None:
                                # If receipt_no is defined, reduce it by the quantity
                                product.receipt_no -= quantity
                                product.save()  # Save the product instance      

                elif receipt == "No Receipt":
                    if package:
                        if product.package >= package:
                            product.package -= package
                            quantity = package * product.piece
                            item_data['quantity'] = quantity
                            if quantity >  product.stock:
                                # This shows the quantity as long as it is not greater than stock
                                raise serializers.ValidationError({
                                    "error": f"Insufficient quantity for {product.name}. Available stock is {product.stock}, but {quantity} quantity was requested."
                                })
                            product.stock -= quantity
                            product.save()  # Save the product instance

                        elif product.package < package:
                            # This shows the quantity as long as it is not greater than stock
                            raise serializers.ValidationError({"error": f"Insufficient package for {product.name}. Available package is {product.package}, but {package} package was requested."})   
                    
                    elif package is None:
                        if quantity >  product.stock:
                            # This shows the quantity as long as it is not greater than stock
                            raise serializers.ValidationError({
                                "error": f"Insufficient stock for {product.name}. Available stock is {product.stock}, but {quantity} quantity was requested."
                            })
                        # Calculate the remaining stock and adjust the package count
                        remaining_stock = product.stock - quantity
                        if product.piece is not None and product.package is not None:
                            # If piece and package are defined, calculate remaining packages
                            remaining_packages = remaining_stock // piece  # Calculate remaining packages
                            product.package = remaining_packages
                            product.stock = remaining_stock
                            product.save()
                            
                        else:
                            product.stock -= quantity
                            product.save()  # Save the product instance  

                total_price = unit_price * item_data['quantity']
                vat = total_price * Decimal(0.15)
                receipt_total_price = total_price + vat

                # Create the OrderItem and associate with the Order
                OrderItem.objects.create(order=order, price=total_price, **item_data)
                # Adding it into the log with every itration
                create_order_log(
                    user = user.name,
                    action="Create",
                    model_name="Order",
                    object_id=order.id,
                    customer_info = order.customer,
                    product_name = item_data['product'].name,
                    quantity = item_data['quantity'],
                    price = total_price,
                    changes_on_update = "Created Order Item",
                )
                # Adding it into the report with every itration
                if order.customer is None and order.receipt == "Receipt":
                    create_order_report(
                        user = user.name,
                        customer_name = "Anonymous Customer", 
                        customer_phone = "0000000000",
                        customer_tin_number = "000000000",
                        order_date = order.order_date,
                        order_id = order.id,
                        item_receipt = item_data['item_receipt'],
                        unit = item_data['unit'],
                        product_name = item_data['product'].name,
                        product_price = unit_price,
                        quantity = item_data['quantity'],
                        sub_total = total_price,
                        vat = vat,
                        payment_status = order.payment_status,
                        total_amount = receipt_total_price
                    )
                elif order.customer is not None and order.receipt == "Receipt":
                    create_order_report(
                        user = user.name,
                        customer_name = order.customer.name,
                        customer_phone = order.customer.phone,
                        customer_tin_number = order.customer.tin_number,
                        order_date = order.order_date,
                        order_id = order.id,
                        item_receipt = item_data['item_receipt'],
                        unit = item_data['unit'],
                        product_name = item_data['product'].name,
                        product_price = unit_price,
                        quantity = item_data['quantity'],
                        sub_total = total_price,
                        vat = vat,
                        payment_status = order.payment_status,
                        total_amount = receipt_total_price
                    )
                elif order.customer is not None and order.receipt == "No Receipt":
                    create_order_report(
                        user = user.name,
                        customer_name = order.customer.name,
                        customer_phone = order.customer.phone,
                        customer_tin_number = order.customer.tin_number,
                        order_date = order.order_date,
                        order_id = order.id,
                        item_receipt = item_data['item_receipt'],
                        unit = item_data['unit'],
                        product_name = item_data['product'].name,
                        product_price = unit_price,
                        quantity = item_data['quantity'],
                        sub_total = total_price,
                        vat = 0,
                        payment_status = order.payment_status,
                        total_amount = total_price
                    )
                elif order.customer is None and order.receipt == "No Receipt":
                    create_order_report(
                        user = user.name,
                        customer_name = "Anonymous Customer", 
                        customer_phone = "0000000000",
                        customer_tin_number = "000000000",
                        order_date = order.order_date,
                        order_id = order.id,
                        item_receipt = item_data['item_receipt'],
                        unit = item_data['unit'],
                        product_name = item_data['product'].name,
                        product_price = unit_price,
                        quantity = item_data['quantity'],
                        sub_total = total_price,
                        vat = 0,
                        payment_status = order.payment_status,
                        total_amount = total_price
                    )


            order.save()
            
            total_amount = Decimal(str(order.total_amount or 0))  # Convert to Decimal
            paid = Decimal(str(paid_amount or 0))  # Convert to Decimal

            if payment_status == 'Pending':
                order.unpaid_amount = max(total_amount - paid, Decimal('0.00'))
                order.save()
            elif payment_status == 'Unpaid':
                order.paid_amount = Decimal('0.00')
                order.unpaid_amount = total_amount
                order.save()
            elif payment_status == 'Paid':
                order.paid_amount = total_amount
                order.unpaid_amount = Decimal('0.00')
                order.save()

            new_unpaid_amount = total_amount - paid

            # 🔍 Log changes

            OrderPaymentLog.objects.create(
                order=order,
                customer=order.customer,
                change_type="Status Create",
                field_name="payment_status",
                old_value=0,
                new_value=new_payment_status,
                user=user.name
            )

            OrderPaymentLog.objects.create(
                order=order,
                customer=order.customer,
                change_type="Payment Create",
                field_name="paid_amount",
                old_value=0,
                new_value=new_paid_amount,
                user=user.name
            )

            OrderPaymentLog.objects.create(
                order=order,
                customer=order.customer,
                change_type="Payment Create",
                field_name="Unpaid Amount",
                old_value=0,
                new_value=new_unpaid_amount,
                user=user.name
            )

        
        return order


    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        # print("items", items_data)

        user = self.context['request'].user
        user_role = user.role
        user_name = user.name
        # Update order fields directly
        instance.customer = validated_data.get('customer', instance.customer)
        instance.status = validated_data.get('status', instance.status)
        new_status = validated_data.get('status')
        new_paid = validated_data.get('paid_amount')

        old_status = instance.payment_status
        old_paid = instance.paid_amount
        old_unpaid = instance.unpaid_amount

        # print("old_paid", old_paid)

        # If a salesman tries to cancel, set to Pending and raise error
        if new_status == 'Cancelled' and user_role == 'Salesman' or new_status == 'Cancelled' and user_role == 'Sales Manager':
            instance.status = 'Pending'
            instance.save()

            total_quantity = sum(item.quantity for item in instance.items.all())
            total_price = sum(item.price for item in instance.items.all())
            create_order_log(
                user=user_name,
                action="Request Cancel",
                model_name="Order",
                object_id=instance.id,
                customer_info=instance.customer,
                product_name="Whole Order",
                quantity=total_quantity,
                price=total_price,
                changes_on_update="Salesman requested cancellation"
            )

            raise serializers.ValidationError({
                "error": "You cannot cancel orders directly. Your cancellation request is now pending manager/admin approval."
            })

        # Update Performa basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        

        if items_data is not None:
            existing_items = {item.id: item for item in instance.items.all()}
            sent_ids = [item.get('id') for item in items_data if item.get('id')]
            # print("sent_id",  sent_ids)

            # Delete items not included in the update
            for item in instance.items.all():
                if item.id not in sent_ids:
                    item.delete()

            # Add or update items
            for item_data in items_data:
                item_id = item_data.get('id')

                user = self.context['request'].user
                user_role = user.role
                user_name = user.name
                # Update order fields directly
                new_quantity = item_data.get('quantity')
                new_status = item_data.get('status')
                new_package = item_data.get('package')
                new_unit_price = item_data.get('unit_price')


                if item_id and item_id in existing_items:
                    item = existing_items[item_id]
                    
                    product = item.product  # Access the product from the existing order item
                    quantity = item.quantity
                    receipt = item.order.receipt  # Access the receipt from the order
                    package = item.package
                    unit_price = item.unit_price



                    # If a salesman tries to cancel, set to Pending and raise error
                    if new_status == 'Cancelled' and user_role == 'Salesman':
                        item.status = 'Pending'
                        item.save()

                        create_order_log(
                            user=user_name,
                            action="Request Cancel",
                            model_name="OrderItem",
                            object_id=item.id,
                            customer_info=item.order.customer,
                            product_name=item.product.name,
                            quantity=item.quantity,
                            price=item.price,
                            changes_on_update="Salesman requested cancellation"
                        )

                        raise serializers.ValidationError({
                            "error": "You cannot cancel orders directly. Your cancellation request is now pending manager/admin approval."
                        })


                    if new_quantity and item.status == 'Cancelled':
                        raise serializers.ValidationError({
                            "error": f"The order is already cancelled."
                        })
                    
                    if new_quantity and new_quantity <= 0:
                        raise serializers.ValidationError({
                            "error": f"Quantity must be greater than zero."
                        })
                    
                    if new_status:
                        if new_status == 'Cancelled':
                            product.stock += item.quantity
                            item.quantity = 0
                            item.unit_price = 0
                            item.product_price = 0
                            item.price = 0
                            item.cost = 0
                            item.status = 'Cancelled' 
                            if product.package is not None and package is not None:
                                product.package += package
                                item.package = 0
                            if receipt == "Receipt":
                                if product.receipt_no is not None:
                                    product.receipt_no += quantity
                            product.save()
                            item.save()
                        elif new_status == 'Done':
                            item.status = 'Done' 
                            item.save()



                    if new_quantity and new_quantity > 0 and item.status == 'Done':
                        # Calculate the difference between new and existing quantity
                        quantity_difference = new_quantity - quantity

                        piece = product.piece

                        if product.stock >= quantity_difference:  # Ensure there is enough stock
                            # Reduce stock by the order quantity_difference

                            if receipt == "Receipt":
                                if package:
                                    if product.package >= package:
                                        product.package -= package
                                        product.stock -= quantity_difference
                                        if product.receipt_no is not None:
                                            product.receipt_no -= quantity_difference
                                        product.save()  # Save the product item
                                    elif product.package < package:
                                        # raise ValidationError("The amount of package is insufficient.")
                                        raise serializers.ValidationError({
                                            "error": f"The amount of package is insufficient."
                                        })
                                        
                                elif package is None:
                                    if piece is not None:
                                        # Calculate the remaining stock and adjust the package count
                                        remaining_stock = product.stock - quantity_difference
                                        remaining_packages = remaining_stock // piece  # Calculate remaining packages
                                        product.package = remaining_packages
                                        product.stock = remaining_stock
                                        if product.receipt_no is not None:
                                            product.receipt_no -= quantity_difference
                                        product.save()  # Save the product item
                                    else:
                                        remaining_stock = product.stock - quantity_difference
                                        product.stock = remaining_stock
                                        product.save()  # Save the product item

                            elif receipt == "No Receipt":
                                if package:
                                    if product.package >= package:
                                        product.package -= package
                                        product.stock -= quantity_difference
                                        product.save()  # Save the product item
                                    elif product.package < package:
                                        raise serializers.ValidationError({
                                                "error": f"The amount of package is insufficient."
                                            })
                                elif package is None:
                                    if piece is not None:
                                        # Calculate the remaining stock and adjust the package count
                                        remaining_stock = product.stock - quantity_difference
                                        remaining_packages = remaining_stock // piece  # Calculate remaining packages
                                        product.package = remaining_packages
                                        product.stock = remaining_stock
                                        product.save()  # Save the product item
                                    else:
                                        remaining_stock = product.stock - quantity_difference
                                        product.stock = remaining_stock
                                        product.save()  # Save the product item

                                
                        else:
                            raise serializers.ValidationError({
                                    "error": f"Insufficient stock for {product.name}. Available stock is {product.stock}, but {quantity} was requested."
                                })
                        # Update the item's quantity
                        item.quantity = new_quantity

                        # The total price without VAT
                        if unit_price > 0 and new_unit_price is None:
                            item.price = unit_price * item.quantity
                        elif new_unit_price is not None:
                            item.unit_price = new_unit_price
                            item.price = new_unit_price * item.quantity
                        else:
                            item.price = product.selling_price * item.quantity

                    item.save()


                    for attr, value in item_data.items():
                        if attr != 'id':
                            setattr(item, attr, value)

                    item.price = item.quantity * item.unit_price
                    item.save()
                else:
                    # Remove 'id' if present, as it's not needed for new order item creation
                    item_data.pop('id', None)
                    item_data.pop('order', None)

                    product = item_data['product']
                    quantity = item_data.get('quantity')
                    receipt = instance.receipt
                    item_data['item_receipt'] = receipt
                    package = item_data.get('package')
                    unit_price = item_data.get('unit_price', product.selling_price)  # Default to product's selling price if not provided
                    piece = product.piece

                    if quantity is not None and product.stock < quantity:
                        raise serializers.ValidationError({
                            "error": f"Insufficient stock for {product.name}. Available stock is {product.stock}, but {quantity} was requested."
                        })
                    
                    if package is not None and product.package < package:
                        raise serializers.ValidationError({
                            "error": f"Insufficient package for {product.name}. Available package is {product.package}, but {package} was requested."
                        })
                    
                    if receipt == "Receipt":
                        if package:
                            if product.package >= package:
                                product.package -= package
                                quantity = package * product.piece
                                item_data['quantity'] = quantity
                                if quantity >  product.stock:
                                    raise serializers.ValidationError({
                                        "error": f"Insufficient stock for {product.name}. Available stock is {product.stock}, but {quantity} was requested."
                                    })
                                product.stock -= quantity
                                if product.receipt_no is not None:
                                    product.receipt_no -= quantity
                                product.save()  # Save the product instance

                            elif product.package < package:
                                raise serializers.ValidationError({"error": f"Insufficient package for {product.name}. Available package is {product.package}, but {package} was requested."})   
                        
                        elif package is None:
                            # Calculate the remaining stock and adjust the package count
                            remaining_stock = product.stock - quantity
                            if product.piece is not None and product.package is not None:
                                # If piece and package are defined, calculate remaining packages
                                remaining_packages = remaining_stock // piece  # Calculate remaining packages
                                product.package = remaining_packages
                                product.stock = remaining_stock
                                product.save()
                                if product.receipt_no is not None:
                                    # If receipt_no is defined, reduce it by the quantity
                                    product.receipt_no -= quantity
                                    product.save()  # Save the product instance
                            else:
                                product.stock -= quantity
                                product.save()  # Save the product instance  
                                if product.receipt_no is not None:
                                    # If receipt_no is defined, reduce it by the quantity
                                    product.receipt_no -= quantity
                                    product.save()  # Save the product instance      

                    elif receipt == "No Receipt":
                        if package:
                            if product.package >= package:
                                product.package -= package
                                quantity = package * piece
                                item_data['quantity'] = quantity
                                if quantity >  product.stock:
                                    # This shows the quantity as long as it is not greater than stock
                                    raise serializers.ValidationError({
                                        "error": f"Insufficient stock for {product.name}. Available stock is {product.stock}, but quantity {quantity} was requested."
                                    })
                                product.stock -= quantity
                                product.save()  # Save the product instance

                            elif product.package < package:
                                # This shows the quantity as long as it is not greater than stock
                                raise serializers.ValidationError({"error": f"Insufficient stock for {product.name}. Available package is {product.package}, but package {package} was requested."})   
                        
                        elif package is None:
                            # Calculate the remaining stock and adjust the package count
                            remaining_stock = product.stock - quantity
                            if product.piece is not None and product.package is not None:
                                # If piece and package are defined, calculate remaining packages
                                remaining_packages = remaining_stock // piece  # Calculate remaining packages
                                product.package = remaining_packages
                                product.stock = remaining_stock
                                product.save()
                                
                            else:
                                product.stock -= quantity
                                product.save()  # Save the product instance  

                    total_price = unit_price * item_data['quantity']
                    
                    # update_payment_status_on_new_order_item(order=instance, new_items=None)


                    if instance.pk is None:
                       instance.save()
                    OrderItem.objects.create(
                        order=instance,
                        price=total_price,
                        **item_data
                    )

                    #  Add this line
                    # update_payment_status_on_new_order_item(instance, [new_order_item])

        # # Recalculate sub_total and total
        # sub_total = sum(item.price for item in instance.items.all())
        # instance.sub_total = sub_total
        # instance.total = sub_total + instance.vat
        # Recalculate sub_total and total
        sub_total = sum(item.price for item in instance.items.all())
        instance.sub_total = sub_total
        instance.vat = instance.sub_total * Decimal('0.15')
        instance.total_amount = instance.sub_total + instance.vat

        # instance.paid_amount = validated_data.get('paid_amount', instance.paid_amount)
        # instance.payment_status = validated_data.get('payment_status', instance.payment_status)

        # print(f"Total Amount: {instance.total_amount}")
        # print(f"Paid Amount: {instance.paid_amount}")

        # total_amount = Decimal(str(instance.total_amount or 0))  # Convert to Decimal
        # paid = Decimal(str(instance.paid_amount or 0))  # Convert to Decimal

        if 'paid_amount' in validated_data:
            paid = old_paid + new_paid
            total = Decimal(str(instance.total_amount or 0))
            
            if paid < 0:
                raise serializers.ValidationError("Paid amount cannot be negative")
            if paid > total:
                raise serializers.ValidationError("Paid amount cannot be greater than total amount")
            
            instance.paid_amount = paid
            instance.total_amount = total
            instance.save()

        # need more work when i get home
        # instance.paid_amount += new_paid

        if instance.payment_status == 'Pending':
            instance.unpaid_amount = max(instance.total_amount - instance.paid_amount, Decimal('0.00'))
            if instance.unpaid_amount == Decimal('0.00'):
                instance.payment_status = 'Paid'
            instance.save()
        elif instance.payment_status == 'Unpaid':
            instance.paid_amount = Decimal('0.00')
            instance.unpaid_amount = instance.total_amount
            instance.save()
        elif instance.payment_status == 'Paid':
            instance.paid_amount = instance.total_amount
            instance.unpaid_amount = Decimal('0.00')
            instance.save()
        


        # 🔍 Log changes
        if instance.payment_status != old_status:
            OrderPaymentLog.objects.create(
                order=instance,
                customer=instance.customer,
                change_type="Status Change",
                field_name="payment_status",
                old_value=old_status,
                new_value=instance.payment_status,
                user=instance.user  # Optional if available
            )

        if instance.paid_amount != old_paid:
            OrderPaymentLog.objects.create(
                order=instance,
                customer=instance.customer,
                change_type="Payment Update",
                field_name="paid_amount",
                old_value=old_paid,
                new_value=instance.paid_amount,
                user=instance.user
            )
        
        if instance.unpaid_amount != old_unpaid:
            OrderPaymentLog.objects.create(
                order=instance,
                customer=instance.customer,
                change_type="Payment Update",
                field_name="unpaid_amount",
                old_value=old_unpaid,
                new_value=instance.unpaid_amount,
                user=instance.user
            )


        instance.save()

        return instance


class OrderLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderLog
        fields = '__all__'

class OrderReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = Report
        fields = '__all__'

class ExpenseTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseTypes
        fields = '__all__'
    
    def create(self, validated_data, user=None):
        if user:
            validated_data['user'] = user.name
        return super().create(validated_data)

class OtherExpensesSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherExpenses
        fields = '__all__'

    def create(self, validated_data, user=None):
        if user:
            validated_data['user'] = user.name
        return super().create(validated_data)

class OtherExpensesGetSerializer(serializers.ModelSerializer):
    expense_type = serializers.CharField(source='expense_type.name', read_only=True)

    class Meta:
        model = OtherExpenses
        fields = '__all__'

    def create(self, validated_data, user=None):
        if user:
            validated_data['user'] = user.name
        return super().create(validated_data)

class ProductGetReportSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'category_name', 'description', 'buying_price', 'selling_price', 'stock', 'supplier_name', 'user']


class PurchaseProductSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    class Meta:
        model = PurchaseProduct
        fields = ['id', 'product', 'unit', 'description', 'quantity', 'unit_price', 'total_price']
    
    def update(self, instance, validated_data):
        instance.quantity = validated_data.get('quantity', instance.quantity)
        instance.unit_price = validated_data.get('unit_price', instance.unit_price)

        # Update Products basic fields
        for attr, value in validated_data.items():
            if attr != 'total_price':
                setattr(instance, attr, value)
            else:
                # If update_stocks is provided, update the stock directly
                instance.total_price = instance.quantity * instance.unit_price
        instance.save()

        return instance

class PurchaseExpenseSerializer(serializers.ModelSerializer):
    products = PurchaseProductSerializer(many=True)
    id = serializers.IntegerField(required=False)

    class Meta:
        model = PurchaseExpense
        fields = ['id', 'purchase_date', 'supplier', 'total', 'payment_status', 'paid_amount', 'unpaid_amount', 'user', 'products']

    def create(self, validated_data):
        user = self.context["request"].user
        if user:
            validated_data['user'] = user.name

        purchase_date=timezone.now()
        products_data = validated_data.pop('products')
        expense = PurchaseExpense.objects.create(**validated_data)
        for product_data in products_data:
            PurchaseProduct.objects.create(expense=expense, **product_data)
        return expense
    
    def update(self, instance, validated_data):
        products_data = validated_data.pop('products', [])
        new_paid = validated_data.get('paid_amount', 0)
        instance.payment_status = validated_data.get('payment_status', instance.payment_status)
        print(instance.payment_status)

        old_status = instance.payment_status
        old_paid = instance.paid_amount
        old_unpaid = instance.unpaid_amount

        for attr, value in validated_data.items():
            if attr != 'paid_amount' and attr != 'payment_status':
                setattr(instance, attr, value)
        instance.save()

        # Update or create products
        existing_ids = [p.id for p in instance.products.all()]
        received_ids = [item.get('id') for item in products_data if item.get('id')]

        # Delete products not present in update data
        # for product in instance.products.all():
        #     if product.id not in received_ids:
        #         product.delete()

        for product_data in products_data:
            product_id = product_data.get('id')
            if not product_id:
                print("Creating new product")
                # Create new product
                quantity = int(product_data.get('quantity', 0))
                unit_price = Decimal(str(product_data.get('unit_price', 0)))
                total_price = quantity * unit_price
                PurchaseProduct.objects.create(expense=instance, total_price=total_price, **product_data)


        instance.total = instance.products.aggregate(Sum('total_price'))['total_price__sum'] or Decimal('0.00')
        instance.total = Decimal(str(instance.total))
        instance.save()

        if 'paid_amount' in validated_data and instance.payment_status != 'Paid':
            paid = instance.paid_amount + new_paid
            total = Decimal(str(instance.total or 0))
            
            if paid < 0:
                raise serializers.ValidationError("Paid amount cannot be negative")
            if paid > total:
                raise serializers.ValidationError("Paid amount cannot be greater than total amount")
            
            instance.paid_amount = paid
            instance.save()

        if instance.payment_status == 'Paid':
            instance.paid_amount = instance.total
            instance.unpaid_amount = Decimal('0.00')
            instance.payment_status = 'Paid'
        elif instance.payment_status == 'Pending' and instance.total >= instance.paid_amount:
            instance.unpaid_amount = max(instance.total - instance.paid_amount, Decimal('0.00'))
            if instance.unpaid_amount == Decimal('0.00'):
                instance.payment_status = 'Paid'   
        elif instance.payment_status == 'Unpaid':
            instance.paid_amount = Decimal('0.00')
            instance.unpaid_amount = instance.total
            instance.payment_status = 'Unpaid'
        instance.save()

        # 🔍 Log changes
        if instance.payment_status != old_status:
            ExpensePaymentLog.objects.create(
                expense=instance,
                supplier=instance.supplier,
                change_type="Status Change",
                field_name="payment_status",
                old_value=old_status,
                new_value=instance.payment_status,
                user=instance.user  # Optional if available
            )

        if instance.paid_amount != old_paid:
            ExpensePaymentLog.objects.create(
                expense=instance,
                supplier=instance.supplier,
                change_type="Payment Update",
                field_name="paid_amount",
                old_value=str(old_paid),
                new_value=str(instance.paid_amount),
                user=instance.user
            )
        
        instance.save()
        return instance

class PurchaseSupplierSerializer(serializers.ModelSerializer):
    expenses = PurchaseExpenseSerializer(many=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = PurchaseSupplier
        fields = ['id', 'supplier', 'supplier_name', 'total_amount', 'payment_status', 'paid_amount', 'unpaid_amount', 'user', 'expenses']
        constraints = [
            UniqueConstraint(fields=['supplier'], name='unique_supplier')
        ]
    
    def create(self, validated_data):
        user = self.context["request"].user
        if user:
            validated_data['user'] = user.name

        user_name = validated_data['user']
        expenses_data = validated_data.pop('expenses')
        total_amount = Decimal('0.00')  # Start total
        supplier = PurchaseSupplier.objects.create(**validated_data)

        try:
            for expense_data in expenses_data:
                products_data = expense_data.pop('products', [])
                paid = expense_data.get('paid_amount')
                payment_status = expense_data.get('payment_status')

                # Calculate total for this expense
                expense_total = sum(Decimal(str(product.get('unit_price', 0))) * int(product.get('quantity', 0)) for product in products_data)
                total_amount += expense_total

                if paid and paid > expense_total:
                    raise serializers.ValidationError("Expense cannot be created with paid amount greater than total amount so re-create the expense by ging to manage purchase")

                if expense_data['payment_status'] == 'Paid':
                    expense_data['paid_amount'] = expense_total
                elif expense_data['payment_status'] == 'Unpaid':
                    expense_data['unpaid_amount'] = expense_total
                elif expense_data['payment_status'] == 'Pending':
                    if expense_data['paid_amount'] > 0:
                        expense_data['unpaid_amount'] = max(expense_total - expense_data['paid_amount'], Decimal('0.00'))
                    elif expense_data['paid_amount'] == 0 or expense_data['paid_amount'] is None:
                        expense_data['unpaid_amount'] = expense_total

                if validated_data['supplier']:
                    expense_supplier_name = validated_data.get('supplier')
                else:
                    expense_supplier_name = None
                    
                # Create the expense with computed total
                expense = PurchaseExpense.objects.create(supplier_level=supplier, supplier=expense_supplier_name, user=user_name, total=expense_total, **expense_data)

                for product_data in products_data:
                    quantity = int(product_data.get('quantity', 0))
                    unit_price = Decimal(str(product_data.get('unit_price', 0)))
                    total_price = quantity * unit_price
                    PurchaseProduct.objects.create(expense=expense, total_price=total_price, **product_data)


            # After all expenses, update supplier's total_amount
            supplier.total_amount = total_amount
            supplier.save(update_fields=['total_amount'])

            return supplier

        except Exception as e:
            # Optional: rollback or raise a validation error
            raise serializers.ValidationError({"detail": f"Failed to create supplier: {str(e)}"})

    def update(self, instance, validated_data):
        expenses_data = validated_data.pop('expenses', [])
        # Capture original values before update
        old_status = instance.payment_status
        old_paid = instance.paid_amount
        old_unpaid = instance.unpaid_amount

        supplier_name = instance.supplier.name or None

        # Update supplier fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        for expense_data in expenses_data:
            expense_id = expense_data.get('id')
            products_data = expense_data.pop('products', [])

            if not expense_id:
                # Create new Expense
                paid_amount = expense_data.get('paid_amount', None)
                unpaid_amount = expense_data.get('unpaid_amount', None)
                expense_total = sum(Decimal(str(product.get('unit_price', 0))) * int(product.get('quantity', 0)) for product in products_data)
                unpaid_amount = expense_total - paid_amount if paid_amount else expense_total

                if paid_amount and paid_amount > expense_total:
                    raise serializers.ValidationError("Expense cannot be created with paid amount greater than total amount so re-create the expense by ging to manage purchase")

                
                # Inside your for-loop where you create a new expense:
                update_payment_status_on_new_expense_or_product(supplier=instance, expense=None)
                

                # Avoid duplicate 'total' key error
                expense_data.pop('total', None)
                expense = PurchaseExpense.objects.create(supplier_level=instance, supplier=supplier_name, total=expense_total, unpaid_amount=unpaid_amount, **expense_data)

                for product_data in products_data:
                    product_id = product_data.get('id')
                    if product_id:
                        # Update existing product
                        product = PurchaseProduct.objects.get(id=product_id, expense=instance)
                        for attr, value in product_data.items():
                            setattr(product, attr, value)
                        product.save()
                    else:
                        # Create new product
                        quantity = int(product_data.get('quantity', 0))
                        unit_price = Decimal(str(product_data.get('unit_price', 0)))
                        total_price = quantity * unit_price

                        PurchaseProduct.objects.create(expense=expense, total_price=total_price, **product_data)

        # Syncronizing the total, paid and unpaid with the expenses
        instance.total_amount = sum(expense.total for expense in instance.expenses.all())
        instance.paid_amount = sum(expense.paid_amount for expense in instance.expenses.all())        
        instance.unpaid_amount = sum(expense.unpaid_amount for expense in instance.expenses.all())
        
        # Updating the status of supplier
        total_amount = Decimal(str(instance.total_amount or 0))
        paid = Decimal(str(instance.paid_amount or 0))

        if instance.payment_status == 'Pending':
            if paid > 0:
                instance.unpaid_amount = max(total_amount - paid, Decimal('0.00'))
            elif paid == 0:
                instance.unpaid_amount = total_amount
        elif instance.payment_status == 'Unpaid':
            instance.paid_amount = Decimal('0.00')
            instance.unpaid_amount = total_amount
        elif instance.payment_status == 'Paid':
            instance.paid_amount = total_amount
            instance.unpaid_amount = Decimal('0.00')

        
        # Log changes
        if instance.payment_status != old_status:
            SupplierPaymentLog.objects.create(
                supplier=instance,
                change_type="Status Change",
                field_name="payment_status",
                old_value=old_status,
                new_value=instance.payment_status,
                user=instance.user  # Optional if available
            )

        if instance.paid_amount != old_paid:
            SupplierPaymentLog.objects.create(
                supplier=instance,
                change_type="Payment Update",
                field_name="paid_amount",
                old_value=str(old_paid),
                new_value=str(instance.paid_amount),
                user=instance.user
            )

        instance.save()            

        return instance


class SupplierPaymentLogSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.supplier.name', read_only=True)

    class Meta:
        model = SupplierPaymentLog
        fields = ['id', 'supplier_name', 'change_type', 'field_name', 'old_value', 'new_value', 'user', 'supplier', 'timestamp']

class ExpensePaymentLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpensePaymentLog
        fields = '__all__'

class OrderPaymentLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderPaymentLog
        fields = '__all__'


# New Performa Serializer
class PerformaProductSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    class Meta:
        model = PerformaProduct
        fields = ['id', 'product', 'unit', 'description', 'quantity', 'unit_price', 'total_price']
    
    def update(self, instance, validated_data):
        instance.quantity = validated_data.get('quantity', instance.quantity)
        instance.unit_price = validated_data.get('unit_price', instance.unit_price)

        # Update Products basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        instance.total_price = instance.quantity * instance.unit_price
        instance.save()

        return instance

class PerformaPerformaSerializer(serializers.ModelSerializer):
    products = PerformaProductSerializer(many=True)
    id = serializers.IntegerField(required=False)

    class Meta:
        model = PerformaPerforma
        fields = ['id', 'issued_date', 'customer', 'receipt', 'sub_total', 'vat', 'total', 'user', 'products']

    def create(self, validated_data):
        user = self.context["request"].user
        if user:
            validated_data['user'] = user.name

        issued_date=timezone.now()
        products_data = validated_data.pop('products')
        expense = PerformaPerforma.objects.create(**validated_data)
        for product_data in products_data:
            PerformaProduct.objects.create(expense=expense, **product_data)
        return expense
    
    def update(self, instance, validated_data):
        products_data = validated_data.pop('products', [])
        receipt = validated_data.get('receipt', instance.receipt)

        # Update or create products
        existing_ids = [p.id for p in instance.products.all()]
        received_ids = [item.get('id') for item in products_data if item.get('id')]

        # Delete products not present in update data
        for product in instance.products.all():
            if product.id not in received_ids:
                product.delete()

        for product_data in products_data:
            product_id = product_data.get('id')
            if product_id:
                # Update existing product
                product = PerformaProduct.objects.get(id=product_id, performa=instance)
                for attr, value in product_data.items():
                    setattr(product, attr, value)
                product.save()
            else:
                # Create new product
                quantity = int(product_data.get('quantity', 0))
                unit_price = Decimal(str(product_data.get('unit_price', 0)))
                total_price = quantity * unit_price
                PerformaProduct.objects.create(performa=instance, total_price=total_price, **product_data)

        sub_total = sum(item.total_price for item in instance.products.all())
        instance.sub_total = sub_total
        if receipt == "Receipt":
            instance.vat = sub_total * Decimal('0.15')
        else:
            instance.vat = 0
        instance.total = sub_total + instance.vat
        instance.save()
        
        return instance

class PerformaCustomerSerializer(serializers.ModelSerializer):
    performas = PerformaPerformaSerializer(many=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = PerformaCustomer
        fields = ['id', 'customer', 'customer_name', 'user', 'performas']
        constraints = [
            UniqueConstraint(fields=['customer'], name='unique_customer')
        ]
    
    def create(self, validated_data):
        user = self.context["request"].user
        if user:
            validated_data['user'] = user.name

        user_name = validated_data['user']
        performas_data = validated_data.pop('performas')
        total_amount = Decimal('0.00')  # Start total
        customer = PerformaCustomer.objects.create(**validated_data)

        print(f"user name for Customer : {user_name}")

        try:
            for performa_data in performas_data:
                products_data = performa_data.pop('products', [])
                receipt = performa_data.get('receipt', 'Receipt')

                # Calculate total for this expense
                performa_sub_total = sum(Decimal(str(product.get('unit_price', 0))) * int(product.get('quantity', 0)) for product in products_data)
                if receipt == "Receipt":
                    performa_vat = performa_sub_total * Decimal('0.15')
                else:
                    performa_vat = 0
                performa_total = performa_sub_total + performa_vat

                total_amount += performa_total

                if validated_data['customer']:
                    performa_customer_name = validated_data.get('customer')
                else:
                    performa_customer_name = "Customer"
                    
                # Create the expense with computed total
                performa = PerformaPerforma.objects.create(customer_level=customer, user=user_name, total=performa_total, sub_total=performa_sub_total, vat=performa_vat, customer=performa_customer_name, **performa_data)

                for product_data in products_data:
                    quantity = int(product_data.get('quantity', 0))
                    unit_price = Decimal(str(product_data.get('unit_price', 0)))
                    total_price = quantity * unit_price
                    PerformaProduct.objects.create(performa=performa, total_price=total_price, **product_data)

            return customer

        except Exception as e:
            # Optional: rollback or raise a validation error
            raise serializers.ValidationError({"detail": f"Failed to create customer: {str(e)}"})

    def update(self, instance, validated_data):
        performas_data = validated_data.pop('performas', [])

        customer_name = instance.customer.name

        # Update supplier fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        existing_ids = [e.id for e in instance.performas.all()]
        received_ids = [item.get('id') for item in performas_data if item.get('id')]

        # Delete expenses not in request
        for performa in instance.performas.all():
            if performa.id not in received_ids:
                performa.delete()

        for performa_data in performas_data:
            print(performa_data)
            performa_id = performa_data.get('id')
            products_data = performa_data.pop('products', [])

            if performa_id:
                # Update existing expense
                performa = PerformaPerforma.objects.get(id=performa_id, customer_level=instance)
                performa_serializer = PerformaPerformaSerializer(instance=performa, data={**performa_data, 'products': products_data})
                performa_serializer.is_valid(raise_exception=True)
                # performa_serializer.save()

            else:
                # Create new Performa
                performa_sub_total = sum(Decimal(str(product.get('unit_price', 0))) * int(product.get('quantity', 0)) for product in products_data)
                receipt = performa_data.get('receipt', 'Receipt')
                if receipt == "Receipt":
                    performa_vat = performa_sub_total * Decimal('0.15')
                else:
                    performa_vat = 0
                performa_total = performa_sub_total + performa_vat
                # Avoid duplicate 'total' key error
                performa_data.pop('total', None)
                performa = PerformaPerforma.objects.create(customer_level=instance, customer=customer_name, total=performa_total, sub_total=performa_sub_total, vat=performa_vat, **performa_data)

                for product_data in products_data:
                    product_id = product_data.get('id')
                    if product_id:
                        # Update existing product
                        product = PerformaProduct.objects.get(id=product_id, performa=instance)
                        for attr, value in product_data.items():
                            setattr(product, attr, value)
                        product.save()
                    else:
                        # Create new product
                        quantity = int(product_data.get('quantity', 0))
                        unit_price = Decimal(str(product_data.get('unit_price', 0)))
                        total_price = quantity * unit_price

                        PerformaProduct.objects.create(performa=performa, total_price=total_price, **product_data)

        instance.save()            

        return instance
