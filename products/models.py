
from django.db import models


class Product(models.Model):
    code = models.CharField(max_length=10, unique=True, verbose_name="Κωδικός")
    name = models.CharField(max_length=120, unique=True, verbose_name="Περιγραφή")
    barcode = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "products_product"

    def __str__(self):
        return self.name