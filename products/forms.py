from typing import Any

from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['code', 'name', 'price', 'quantity', 'barcode', 'description']

    def clean_price(self):
        price: Any | None = self.cleaned_data.get('price')
        if price < 0:
            raise forms.ValidationError("Η τιμή δεν μπορεί να είναι αρνητική!")
        return price
