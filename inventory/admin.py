from django.contrib import admin
from .models import Category, Supplier, Order, OrderItem, CustomerInfo, Product

# Register your models here.

admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Product)
admin.site.register(CustomerInfo)
admin.site.register(Order)
admin.site.register(OrderItem)