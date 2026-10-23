from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'
    # This replaces the generic folder name "Products" in the admin dashboard panel:
    verbose_name = 'Διαχείριση Αποθεμάτων Nexus'