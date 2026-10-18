from django.urls import path
from . import views
urlpatterns = [
    path('home/', views.home_view, name='home_view'),
    path('list/', views.product_list_view, name='product_list_view'),
    path('sync/', views.sync_products, name='sync_products'),
    path('add/', views.product_create, name='product_add'),
    path('edit/<int:pk>/', views.product_edit, name='product_edit'),
    path('delete/<int:pk>/', views.product_delete, name='product_delete'),

    path('api/products/', views.api_product_list, name='api_product_list'),
]