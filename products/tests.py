"""Tests for the products app.

Run them with:
    python manage.py test

Django creates a separate, empty test database for every run,
so these tests never touch your real db.sqlite3.
"""
from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .forms import ProductForm
from .models import Product


def make_product(**overrides):
    """Create a product with sensible defaults; override any field you need."""
    data = {
        "code": "A100",
        "name": "Office chair",
        "price": Decimal("89.90"),
        "quantity": Decimal("12"),
    }
    data.update(overrides)
    return Product.objects.create(**data)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class ProductModelTests(TestCase):
    def test_str_returns_name(self):
        product = make_product(name="Desk lamp")
        self.assertEqual(str(product), "Desk lamp")

    def test_code_must_be_unique(self):
        make_product(code="A100", name="First")
        with self.assertRaises(IntegrityError):
            make_product(code="A100", name="Second")

    def test_name_must_be_unique(self):
        make_product(code="A100", name="Same name")
        with self.assertRaises(IntegrityError):
            make_product(code="B200", name="Same name")


# ---------------------------------------------------------------------------
# Form validation
# ---------------------------------------------------------------------------
class ProductFormTests(TestCase):
    def form_data(self, **overrides):
        data = {"code": "A100", "name": "Office chair", "price": "10.00", "quantity": "5"}
        data.update(overrides)
        return data

    def test_valid_data_is_accepted(self):
        form = ProductForm(data=self.form_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_negative_price_is_rejected(self):
        form = ProductForm(data=self.form_data(price="-1"))
        self.assertFalse(form.is_valid())
        self.assertIn("price", form.errors)

    def test_zero_price_is_allowed(self):
        form = ProductForm(data=self.form_data(price="0"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_required_fields(self):
        form = ProductForm(data={})
        self.assertFalse(form.is_valid())
        for field in ("code", "name", "price", "quantity"):
            self.assertIn(field, form.errors)

    def test_barcode_and_description_are_optional(self):
        form = ProductForm(data=self.form_data(barcode="", description=""))
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_code_is_rejected(self):
        make_product(code="A100", name="Existing")
        form = ProductForm(data=self.form_data(code="A100", name="New one"))
        self.assertFalse(form.is_valid())
        self.assertIn("code", form.errors)


# ---------------------------------------------------------------------------
# Pages (CRUD views)
# ---------------------------------------------------------------------------
class ProductViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="staff", password="testpass123")
        self.client.force_login(user)

    def test_root_redirects_to_home(self):
        response = self.client.get("/")
        self.assertRedirects(response, reverse("home_view"))

    def test_home_page_loads(self):
        response = self.client.get(reverse("home_view"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "products/home.html")

    def test_list_shows_products(self):
        make_product(name="Office chair")
        response = self.client.get(reverse("product_list_view"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Office chair")

    def test_list_shows_empty_message_when_no_products(self):
        response = self.client.get(reverse("product_list_view"))
        self.assertContains(response, "Η βάση δεδομένων είναι άδεια")

    def test_create_product(self):
        response = self.client.post(reverse("product_add"), {
            "code": "N1", "name": "New product", "price": "5.50", "quantity": "3",
        })
        self.assertRedirects(response, reverse("product_list_view"))
        product = Product.objects.get(code="N1")
        self.assertEqual(product.price, Decimal("5.50"))

    def test_create_with_invalid_data_shows_form_again(self):
        response = self.client.post(reverse("product_add"), {
            "code": "N1", "name": "Bad price", "price": "-5", "quantity": "1",
        })
        self.assertEqual(response.status_code, 200)  # form re-rendered, no redirect
        self.assertFalse(Product.objects.exists())

    def test_edit_product(self):
        product = make_product()
        response = self.client.post(reverse("product_edit", args=[product.pk]), {
            "code": product.code, "name": "Renamed", "price": "1.00", "quantity": "1",
        })
        self.assertRedirects(response, reverse("product_list_view"))
        product.refresh_from_db()
        self.assertEqual(product.name, "Renamed")

    def test_edit_missing_product_returns_404(self):
        response = self.client.get(reverse("product_edit", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_delete_page_asks_for_confirmation_without_deleting(self):
        product = make_product()
        response = self.client.get(reverse("product_delete", args=[product.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

    def test_delete_product_on_post(self):
        product = make_product()
        response = self.client.post(reverse("product_delete", args=[product.pk]))
        self.assertRedirects(response, reverse("product_list_view"))
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------
class ProductApiTests(APITestCase):
    def setUp(self):
        user = User.objects.create_user(username="api-user", password="testpass123")
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_returns_empty_list(self):
        response = self.client.get(reverse("api-product-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_returns_products_as_json(self):
        make_product(code="A100", name="Office chair", barcode="123")
        data = self.client.get(reverse("api-product-list")).json()["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["code"], "A100")
        self.assertEqual(data[0]["name"], "Office chair")
        self.assertEqual(data[0]["price"], "89.90")
        self.assertEqual(data[0]["barcode"], "123")
        self.assertEqual(
            set(data[0]),
            {"id", "code", "name", "price", "quantity", "barcode", "description"},
        )

    def test_create_product(self):
        response = self.client.post(reverse("api-product-list"), {
            "code": "API1", "name": "Created via API", "price": "15.00", "quantity": "4",
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Product.objects.filter(code="API1").exists())

    def test_create_with_negative_price_is_rejected(self):
        response = self.client.post(reverse("api-product-list"), {
            "code": "API2", "name": "Bad price", "price": "-5", "quantity": "1",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("price", response.json())
        self.assertFalse(Product.objects.filter(code="API2").exists())

    def test_create_with_duplicate_code_is_rejected(self):
        make_product(code="A100")
        response = self.client.post(reverse("api-product-list"), {
            "code": "A100", "name": "Another name", "price": "1.00", "quantity": "1",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("code", response.json())

    def test_retrieve_one_product(self):
        product = make_product(code="A100", name="Office chair")
        response = self.client.get(reverse("api-product-detail", args=[product.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Office chair")

    def test_retrieve_missing_product_returns_404(self):
        response = self.client.get(reverse("api-product-detail", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_partial_update_changes_one_field(self):
        product = make_product(price=Decimal("10.00"))
        response = self.client.patch(reverse("api-product-detail", args=[product.pk]), {"price": "12.50"})
        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.price, Decimal("12.50"))

    def test_delete_product(self):
        product = make_product(code="A100", name="Office chair")
        response = self.client.delete(reverse("api-product-detail", args=[product.pk]))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())


# ---------------------------------------------------------------------------
# API search, filtering, ordering and pagination
# ---------------------------------------------------------------------------
class ProductApiQueryTests(APITestCase):
    def setUp(self):
        user = User.objects.create_user(username="api-user", password="testpass123")
        self.client.force_authenticate(user)
        make_product(code="A1", name="Office chair", price=Decimal("89.90"), quantity=Decimal("5"))
        make_product(code="A2", name="Desk lamp", price=Decimal("24.50"), quantity=Decimal("0"))
        make_product(code="A3", name="Standing desk", price=Decimal("449.00"), quantity=Decimal("2"))

    def get_codes(self, params):
        response = self.client.get(reverse("api-product-list"), params)
        self.assertEqual(response.status_code, 200)
        return [item["code"] for item in response.json()["results"]]

    def test_search_by_name(self):
        self.assertEqual(self.get_codes({"search": "desk"}), ["A2", "A3"])

    def test_filter_in_stock(self):
        self.assertEqual(self.get_codes({"in_stock": "true"}), ["A1", "A3"])

    def test_filter_out_of_stock(self):
        self.assertEqual(self.get_codes({"in_stock": "false"}), ["A2"])

    def test_order_by_price_descending(self):
        self.assertEqual(self.get_codes({"ordering": "-price"}), ["A3", "A1", "A2"])

    def test_results_are_paginated(self):
        for i in range(12):
            make_product(code=f"P{i:02}", name=f"Paginated {i}")
        response = self.client.get(reverse("api-product-list"))
        data = response.json()
        self.assertEqual(data["count"], 15)
        self.assertEqual(len(data["results"]), 10)
        self.assertIsNotNone(data["next"])


# ---------------------------------------------------------------------------
# Sync with the external API
#
# We never call the real API in tests: it could be slow, offline, or return
# different data each time. Instead, @patch swaps `requests.get` inside
# products.views for a fake (a Mock) that returns data we control.
# ---------------------------------------------------------------------------
def fake_response(items):
    response = Mock()
    response.json.return_value = {"data": items}
    response.raise_for_status.return_value = None
    return response


@override_settings(ERP_API_URL="https://erp.example.test/api")
@patch("products.views.requests.get")
class SyncProductsTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="staff", password="testpass123")
        self.client.force_login(user)

    def test_creates_products_from_api(self, mock_get):
        mock_get.return_value = fake_response([
            {"code": "S1", "name": "Synced item", "wholesalePrice": 4.5, "qty": 7, "barcode": "999"},
        ])
        response = self.client.post(reverse("sync_products"))

        self.assertRedirects(response, reverse("product_list_view"))
        product = Product.objects.get(code="S1")
        self.assertEqual(product.name, "Synced item")
        self.assertEqual(product.price, Decimal("4.5"))
        self.assertEqual(product.quantity, Decimal("7"))
        self.assertEqual(product.barcode, "999")

    def test_calls_api_with_a_timeout(self, mock_get):
        mock_get.return_value = fake_response([])
        self.client.post(reverse("sync_products"))
        mock_get.assert_called_once()
        self.assertIn("timeout", mock_get.call_args.kwargs)

    def test_updates_existing_product_instead_of_duplicating(self, mock_get):
        make_product(code="S1", name="Old name", price=Decimal("1"))
        mock_get.return_value = fake_response([
            {"code": "S1", "name": "New name", "wholesalePrice": 2, "qty": 1},
        ])
        self.client.post(reverse("sync_products"))

        self.assertEqual(Product.objects.count(), 1)
        product = Product.objects.get(code="S1")
        self.assertEqual(product.name, "New name")
        self.assertEqual(product.price, Decimal("2"))

    def test_running_sync_twice_does_not_create_duplicates(self, mock_get):
        mock_get.return_value = fake_response([
            {"code": "S1", "name": "Item", "wholesalePrice": 1, "qty": 1},
        ])
        self.client.post(reverse("sync_products"))
        self.client.post(reverse("sync_products"))
        self.assertEqual(Product.objects.count(), 1)

    def test_falls_back_to_description_and_retail_price(self, mock_get):
        mock_get.return_value = fake_response([
            {"code": "S2", "description": "Only a description", "retailPrice": 9.99, "qty": 1},
        ])
        self.client.post(reverse("sync_products"))
        product = Product.objects.get(code="S2")
        self.assertEqual(product.name, "Only a description")
        self.assertEqual(product.price, Decimal("9.99"))

    def test_network_error_does_not_crash(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("API is down")
        response = self.client.post(reverse("sync_products"))
        self.assertRedirects(response, reverse("product_list_view"))
        self.assertFalse(Product.objects.exists())

    def test_http_error_does_not_crash(self, mock_get):
        bad = Mock()
        bad.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_get.return_value = bad
        response = self.client.post(reverse("sync_products"))
        self.assertRedirects(response, reverse("product_list_view"))

    def test_empty_response_creates_nothing(self, mock_get):
        mock_get.return_value = fake_response([])
        self.client.post(reverse("sync_products"))
        self.assertFalse(Product.objects.exists())

    def test_duplicate_names_from_api_do_not_crash(self, mock_get):
        mock_get.return_value = fake_response([
            {"code": "D1", "name": "Same name", "wholesalePrice": 1, "qty": 1},
            {"code": "D2", "name": "Same name", "wholesalePrice": 1, "qty": 1},
        ])
        response = self.client.post(reverse("sync_products"))
        self.assertRedirects(response, reverse("product_list_view"))

    def test_success_message_shows_counts(self, mock_get):
        mock_get.return_value = fake_response([
            {"code": "M1", "name": "First", "wholesalePrice": 1, "qty": 1},
            {"code": "M2", "name": "Second", "wholesalePrice": 1, "qty": 1},
        ])
        response = self.client.post(reverse("sync_products"), follow=True)
        self.assertContains(response, "Sync done: 2 created, 0 updated, 0 skipped")

    def test_error_message_when_api_is_down(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("API is down")
        response = self.client.post(reverse("sync_products"), follow=True)
        self.assertContains(response, "Sync failed")
        self.assertContains(response, "API is down")

    def test_sync_with_get_is_not_allowed(self, mock_get):
        response = self.client.get(reverse("sync_products"))
        self.assertEqual(response.status_code, 405)
        mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# Login and logout
# ---------------------------------------------------------------------------
class AuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ellie", password="testpass123")

    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_valid_login_redirects_to_product_list(self):
        response = self.client.post(reverse("login"), {
            "username": "ellie",
            "password": "testpass123",
        })
        self.assertRedirects(response, reverse("product_list_view"))

    def test_wrong_password_shows_error(self):
        response = self.client.post(reverse("login"), {
            "username": "ellie",
            "password": "wrong-password",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Λάθος όνομα χρήστη ή κωδικός")

    def test_logout_with_post_logs_user_out(self):
        self.client.login(username="ellie", password="testpass123")
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("home_view"))

    def test_logout_with_get_is_not_allowed(self):
        self.client.login(username="ellie", password="testpass123")
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)


# ---------------------------------------------------------------------------
# Access control: anonymous visitors must log in first
# ---------------------------------------------------------------------------
class LoginRequiredTests(TestCase):
    def setUp(self):
        self.product = make_product()

    def assert_redirects_to_login(self, url):
        response = self.client.get(url)
        self.assertRedirects(response, f"{reverse('login')}?next={url}")

    def test_add_requires_login(self):
        self.assert_redirects_to_login(reverse("product_add"))

    def test_edit_requires_login(self):
        self.assert_redirects_to_login(reverse("product_edit", args=[self.product.pk]))

    def test_delete_requires_login(self):
        self.assert_redirects_to_login(reverse("product_delete", args=[self.product.pk]))

    def test_sync_requires_login(self):
        self.assert_redirects_to_login(reverse("sync_products"))

    def test_anonymous_delete_post_does_not_delete(self):
        self.client.post(reverse("product_delete", args=[self.product.pk]))
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_product_list_is_still_public(self):
        response = self.client.get(reverse("product_list_view"))
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# API authentication with tokens
# ---------------------------------------------------------------------------
class ApiTokenTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="api-user", password="testpass123")

    def test_obtain_token_with_valid_credentials(self):
        response = self.client.post(reverse("api_token"), {
            "username": "api-user",
            "password": "testpass123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.json())

    def test_obtain_token_with_wrong_password_fails(self):
        response = self.client.post(reverse("api_token"), {
            "username": "api-user",
            "password": "wrong",
        })
        self.assertEqual(response.status_code, 400)

    def test_api_without_token_is_rejected(self):
        response = self.client.get(reverse("api-product-list"))
        self.assertEqual(response.status_code, 401)

    def test_api_with_invalid_token_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token 1234")
        response = self.client.get(reverse("api-product-list"))
        self.assertEqual(response.status_code, 401)

    def test_logged_in_browser_session_can_use_api(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("api-product-list"))
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# Demo ERP endpoint with bundled sample data
# ---------------------------------------------------------------------------
class DemoErpTests(TestCase):
    def test_demo_endpoint_returns_sample_items(self):
        response = self.client.get(reverse("demo_erp_items"))
        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]
        self.assertEqual(len(items), 30)

    def test_every_sample_item_has_the_fields_the_sync_needs(self):
        items = self.client.get(reverse("demo_erp_items")).json()["data"]
        for item in items:
            for field in ("code", "name", "wholesalePrice", "qty"):
                self.assertIn(field, item)

    def test_sample_codes_are_unique(self):
        items = self.client.get(reverse("demo_erp_items")).json()["data"]
        item_codes = [item["code"] for item in items]
        self.assertEqual(len(item_codes), len(set(item_codes)))


@override_settings(ERP_API_URL="https://erp.example.test/api")
@patch("products.views.requests.get")
class SyncWithSampleDataTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="staff", password="testpass123")
        self.client.force_login(user)

    def test_sync_imports_all_sample_items(self, mock_get):
        sample = self.client.get(reverse("demo_erp_items")).json()["data"]
        mock_get.return_value = fake_response(sample)
        response = self.client.post(reverse("sync_products"), follow=True)
        self.assertEqual(Product.objects.count(), 30)
        self.assertContains(response, "Sync done: 30 created, 0 updated, 0 skipped")




# ---------------------------------------------------------------------------
# API documentation (OpenAPI schema and Swagger UI)
# ---------------------------------------------------------------------------
class ProductApiDocsTests(APITestCase):
    def test_schema_is_public(self):
        response = self.client.get(reverse("api_schema"))
        self.assertEqual(response.status_code, 200)

    def test_swagger_ui_is_public(self):
        response = self.client.get(reverse("api_docs"))
        self.assertEqual(response.status_code, 200)

    def test_schema_documents_in_stock_filter(self):
        response = self.client.get(reverse("api_schema"))
        self.assertContains(response, "in_stock")
