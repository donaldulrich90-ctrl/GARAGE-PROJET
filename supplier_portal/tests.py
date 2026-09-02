from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from accounts.forms import SupplierUserCreateForm
from accounts.models import User
from catalog.models import CatalogPart
from inventory.models import Supplier, SupplierExpense, SupplierPart, SupplierStockMovement
from tenants.models import Garage


class SupplierPortalTests(TestCase):
    password = "MotDePasseSolide123!"

    def setUp(self):
        self.garage = Garage.objects.create(name="Garage Centre", city="Ouagadougou")
        self.supplier = Supplier.objects.create(
            garage=self.garage,
            name="Pièces Burkina",
            contact_name="Awa Traoré",
            phone="70000000",
            city="Ouagadougou",
        )
        self.user = User.objects.create_user(
            username="fournisseur_test",
            password=self.password,
            role=User.ROLE_SUPPLIER,
            supplier=self.supplier,
        )
        self.catalog_part = CatalogPart.objects.create(
            reference="FIL-001",
            name="Filtre à huile",
            is_universal=True,
        )
        self.offer = SupplierPart.objects.create(
            garage=self.garage,
            supplier=self.supplier,
            catalog_part=self.catalog_part,
            g_code="OEM-FIL-001",
            unit_price=Decimal("5000.00"),
            quantity_available=4,
            alert_threshold=5,
        )
        self.client.force_login(self.user)

    def select_language(self, language):
        return self.client.post(
            reverse("set_language"),
            {"language": language, "next": reverse("supplier_portal:dashboard")},
        )

    def test_dashboard_displays_supplier_and_platform_stock_alert(self):
        response = self.client.get(reverse("supplier_portal:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pièces Burkina")
        self.assertEqual(response.context["low_stock_count"], 1)
        self.assertEqual(response.context["total_stock"], 4)
        self.assertEqual(len(response.context["period_summaries"]), 3)

    def test_all_main_supplier_pages_render(self):
        page_names = [
            "dashboard",
            "offer_list",
            "offer_create",
            "movement_list",
            "movement_create",
            "sale_list",
            "expense_list",
            "expense_create",
            "report",
            "profile",
            "order_list",
        ]
        for page_name in page_names:
            with self.subTest(page=page_name):
                response = self.client.get(reverse(f"supplier_portal:{page_name}"))
                self.assertEqual(response.status_code, 200)

    def test_english_language_switch_translates_supplier_pages_and_choices(self):
        response = self.select_language("en")
        self.assertRedirects(response, reverse("supplier_portal:dashboard"))

        response = self.client.get(reverse("supplier_portal:dashboard"))
        self.assertContains(response, "Supplier dashboard")
        self.assertContains(response, "Financial results")
        self.assertContains(response, "This week")

        response = self.client.get(reverse("supplier_portal:movement_create"))
        self.assertContains(response, "Movement type")
        self.assertContains(response, "Outgoing / Sale")

        response = self.client.get(reverse("supplier_portal:expense_create"))
        self.assertContains(response, "Inventory purchases")

    def test_english_validation_and_csv_export(self):
        self.select_language("en")
        response = self.client.post(
            reverse("supplier_portal:movement_create"),
            {
                "supplier_part": self.offer.pk,
                "movement_type": SupplierStockMovement.MOVEMENT_OUT,
                "quantity": 8,
                "unit_price": "6000.00",
                "customer_name": "Test customer",
                "payment_method": SupplierStockMovement.PAYMENT_CASH,
            },
        )
        self.assertContains(response, "Available stock: 4.")

        response = self.client.get(
            reverse("supplier_portal:report_export_csv"), {"period": "jour"}
        )
        content = response.content.decode("utf-8-sig")
        self.assertIn("Supplier report", content)
        self.assertIn("SALES", content)

    def test_sale_rejects_quantity_greater_than_available_stock(self):
        response = self.client.post(
            reverse("supplier_portal:movement_create"),
            {
                "supplier_part": self.offer.pk,
                "movement_type": SupplierStockMovement.MOVEMENT_OUT,
                "quantity": 7,
                "unit_price": "6000.00",
                "customer_name": "Client comptoir",
                "payment_method": SupplierStockMovement.PAYMENT_CASH,
                "reason": "Vente",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stock disponible : 4")
        self.assertFalse(SupplierStockMovement.objects.exists())
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.quantity_available, 4)

    def test_valid_sale_updates_stock_and_records_all_details(self):
        response = self.client.post(
            reverse("supplier_portal:movement_create"),
            {
                "supplier_part": self.offer.pk,
                "movement_type": SupplierStockMovement.MOVEMENT_OUT,
                "quantity": 2,
                "unit_price": "6500.00",
                "customer_name": "Garage Wend-Panga",
                "payment_method": SupplierStockMovement.PAYMENT_MOBILE_MONEY,
                "reason": "Vente directe",
            },
        )

        self.assertRedirects(response, reverse("supplier_portal:movement_list"))
        movement = SupplierStockMovement.objects.get()
        self.assertTrue(movement.sale_reference.startswith("VTE-"))
        self.assertEqual(movement.customer_name, "Garage Wend-Panga")
        self.assertEqual(movement.line_total, Decimal("13000.00"))
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.quantity_available, 2)

    def test_expense_and_monthly_report_calculate_net_result(self):
        sale = SupplierStockMovement.objects.create(
            supplier_part=self.offer,
            movement_type=SupplierStockMovement.MOVEMENT_OUT,
            quantity=2,
            unit_price=Decimal("6000.00"),
            customer_name="Client rapport",
            payment_method=SupplierStockMovement.PAYMENT_CASH,
        )
        sale.apply_to_stock()

        response = self.client.post(
            reverse("supplier_portal:expense_create"),
            {
                "date": date.today().isoformat(),
                "category": SupplierExpense.CAT_TRANSPORT,
                "amount": "2000.00",
                "payment_method": SupplierStockMovement.PAYMENT_CASH,
                "reference": "DEP-001",
                "description": "Livraison locale",
            },
        )
        self.assertRedirects(response, reverse("supplier_portal:expense_list"))

        response = self.client.get(reverse("supplier_portal:report"), {"period": "mois"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["summary"]["revenue"], Decimal("12000.00"))
        self.assertEqual(response.context["summary"]["expenses"], Decimal("2000.00"))
        self.assertEqual(response.context["summary"]["net"], Decimal("10000.00"))

    def test_supplier_cannot_access_another_suppliers_expense(self):
        other_supplier = Supplier.objects.create(garage=self.garage, name="Autre fournisseur")
        other_expense = SupplierExpense.objects.create(
            supplier=other_supplier,
            date=date.today(),
            category=SupplierExpense.CAT_OTHER,
            amount=Decimal("1000.00"),
            description="Donnée privée",
        )

        response = self.client.get(
            reverse("supplier_portal:expense_update", kwargs={"pk": other_expense.pk})
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            reverse("supplier_portal:expense_delete", kwargs={"pk": other_expense.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(SupplierExpense.objects.filter(pk=other_expense.pk).exists())

    def test_csv_export_escapes_spreadsheet_formulas(self):
        SupplierStockMovement.objects.create(
            supplier_part=self.offer,
            movement_type=SupplierStockMovement.MOVEMENT_OUT,
            quantity=1,
            unit_price=Decimal("5000.00"),
            customer_name="=DANGEROUS()",
            payment_method=SupplierStockMovement.PAYMENT_CASH,
        )

        response = self.client.get(
            reverse("supplier_portal:report_export_csv"), {"period": "jour"}
        )
        content = response.content.decode("utf-8-sig")
        self.assertEqual(response.status_code, 200)
        self.assertIn("'=DANGEROUS()", content)

    def test_inactive_garage_blocks_supplier_portal(self):
        self.garage.is_active = False
        self.garage.save(update_fields=["is_active"])

        response = self.client.get(reverse("supplier_portal:dashboard"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class SupplierAccountCreationTests(TestCase):
    def test_form_creates_supplier_profile_and_linked_portal_account(self):
        garage = Garage.objects.create(name="Garage Créateur")
        form = SupplierUserCreateForm(
            data={
                "supplier_name": "Distribution Auto Faso",
                "supplier_contact_name": "Moussa Sawadogo",
                "supplier_phone": "70112233",
                "supplier_email": "contact@example.com",
                "supplier_city": "Koudougou",
                "supplier_address": "Secteur 4",
                "supplier_ifu": "IFU-123",
                "supplier_rccm": "RCCM-456",
                "supplier_website": "https://example.com",
                "supplier_notes": "Livraison nationale",
                "username": "distribution_auto",
                "first_name": "Moussa",
                "last_name": "Sawadogo",
                "email": "moussa@example.com",
                "phone": "70112233",
                "password1": "MotDePasseSolide123!",
                "password2": "MotDePasseSolide123!",
            },
            garage=garage,
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save(garage=garage)
        self.assertEqual(user.role, User.ROLE_SUPPLIER)
        self.assertIsNone(user.garage)
        self.assertEqual(user.supplier.garage, garage)
        self.assertEqual(user.supplier.name, "Distribution Auto Faso")
        self.assertEqual(user.supplier.ifu, "IFU-123")
        self.assertEqual(user.supplier.city, "Koudougou")

    def test_supplier_account_form_labels_are_available_in_english(self):
        garage = Garage.objects.create(name="English Garage")
        with translation.override("en"):
            form = SupplierUserCreateForm(garage=garage)
            self.assertEqual(form.fields["supplier_name"].label, "Business name")
            self.assertEqual(form.fields["supplier_logo"].label, "Supplier logo")
            self.assertEqual(form.fields["password2"].label, "Password confirmation")

    def test_admin_can_open_english_supplier_creation_page(self):
        garage = Garage.objects.create(name="Bilingual Garage")
        admin = User.objects.create_user(
            username="garage_admin_en",
            password="MotDePasseSolide123!",
            role=User.ROLE_ADMIN,
            garage=garage,
        )
        self.client.force_login(admin)
        self.client.post(
            reverse("set_language"),
            {"language": "en", "next": reverse("supplier_user_create")},
        )

        response = self.client.get(reverse("supplier_user_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New supplier and portal account")
        self.assertContains(response, "Supplier information")
        self.assertContains(response, "Repair orders")

    def test_login_page_language_can_be_changed_to_english(self):
        self.client.post(
            reverse("set_language"),
            {"language": "en", "next": reverse("login")},
        )

        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in to your account")
        self.assertContains(response, "Automotive garage management")
