import requests
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Product
from .forms import ProductForm
from .serializers import ProductSerializer


def home_view(request):
    return render(request, 'products/home.html')


def product_list_view(request):
    products = Product.objects.all()
    return render(request, 'products/product_list.html', {'products': products})


def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('product_list_view')
    else:
        form = ProductForm()
    return render(request, 'products/product_form.html', {'form': form, 'title': 'Προσθήκη'})


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


def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        return redirect('product_list_view')
    return render(request, 'products/product_confirm_delete.html', {'product': product})


def sync_products(request):
    url = "https://cloudonapi.oncloud.gr/s1services/JS/updateItems/cloudOnTest"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        root_json = response.json()


        items_list = root_json.get('data', [])

        for item in items_list:

            product_name = item.get('name') or item.get('description') or "Χωρίς Όνομα"

            Product.objects.update_or_create(
                code=item.get('code', 'UNKNOWN'),
                defaults={
                    'name': product_name,
                    'price': item.get('wholesalePrice') or item.get('retailPrice') or 0,
                    'quantity': item.get('qty', 10),
                    'barcode': item.get('barcode', None),
                    'description': item.get('description', ''),
                }
            )
    except requests.exceptions.RequestException as e:
        print(f"API Sync Failure: {e}")

    return redirect('product_list_view')



@api_view(['GET'])
def api_product_list(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)