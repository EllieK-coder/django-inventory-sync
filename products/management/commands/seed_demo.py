import json

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from products.models import Product
from products.views import SAMPLE_DATA_FILE

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo1234"


class Command(BaseCommand):
    help = "Create the demo user and load the sample products."

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(username=DEMO_USERNAME)
        user.set_password(DEMO_PASSWORD)
        user.save()

        with open(SAMPLE_DATA_FILE, encoding="utf-8") as f:
            items = json.load(f)["data"]

        for item in items:
            Product.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "price": item["wholesalePrice"],
                    "quantity": item["qty"],
                    "barcode": item.get("barcode"),
                    "description": item.get("description", ""),
                },
            )

        self.stdout.write(self.style.SUCCESS(f"Demo ready: user '{DEMO_USERNAME}', {len(items)} products"))
