from django.contrib import admin
from django.urls import include, path
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('products.urls')),
    path('', lambda request: redirect('home_view', permanent=False)),
]