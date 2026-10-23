from django.contrib import admin

# Register your models here.
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'price', 'quantity')
    search_fields = ('name', 'code')