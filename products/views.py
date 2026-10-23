import json
from pathlib import Path

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, viewsets

from .forms import ProductForm
from .models import Product
from .serializers import ProductSerializer


def home_view(request):
    return render(request, 'products/home.html')


def product_list_view(request):
    products = Product.objects.all()
    return render(request, 'products/product_list.html', {'products': products})


@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('product_list_view')
    else:
        form = ProductForm()
    return render(request, 'products/product_form.html', {'form': form, 'title': 'Προσθήκη'})


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list_view')
    else:
        form = ProductForm(instance=product)
    return render(request, 'products/product_form.html', {'form': form, 'title': 'Επεξεργασία'})


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        return redirect('product_list_view')
    return render(request, 'products/product_confirm_delete.html', {'product': product})


@login_required
@require_POST
def sync_products(request):
    url = settings.ERP_API_URL
    if not url:
        messages.error(request, "Sync failed: ERP_API_URL is not set in .env")
        return redirect('product_list_view')

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        root_json = response.json()

        items_list = root_json.get('data', [])

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for item in items_list:
            product_name = item.get('name') or item.get('description') or "Χωρίς Όνομα"

            try:
                product, created = Product.objects.update_or_create(
                    code=item.get('code', 'UNKNOWN'),
                    defaults={
                        'name': product_name,
                        'price': item.get('wholesalePrice') or item.get('retailPrice') or 0,
                        'quantity': item.get('qty', 10),
                        'barcode': item.get('barcode', None),
                        'description': item.get('description', ''),
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            except IntegrityError:
                print(f"Skipped item {item.get('code')}: duplicate name")
                skipped_count += 1

        summary = f"Sync done: {created_count} created, {updated_count} updated, {skipped_count} skipped"
        messages.success(request, summary)
    except requests.exceptions.RequestException as e:
        messages.error(request, f"Sync failed: {e}")

    return redirect('product_list_view')

@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="in_stock",
                type=bool,
                description="If true, quantity is above 0, if false quantity is 0",
            ),
        ]
    )
)


class ProductViewSet(viewsets.ModelViewSet):
    """Full CRUD API for products: list, create, retrieve, update and delete."""
    queryset = Product.objects.all().order_by("code")
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "name", "barcode", "description"]
    ordering_fields = ["code", "name", "price", "quantity"]

    def get_queryset(self):
        queryset = super().get_queryset()
        in_stock = self.request.query_params.get("in_stock")
        if in_stock == "true":
            queryset = queryset.filter(quantity__gt=0)
        elif in_stock == "false":
            queryset = queryset.filter(quantity=0)
        return queryset

SAMPLE_DATA_FILE = Path(__file__).resolve().parent / "sample_data" / "erp_items.json"


def demo_erp_items(request):
    """Pretend to be an external ERP API by serving the bundled sample data."""
    with open(SAMPLE_DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return JsonResponse(data)