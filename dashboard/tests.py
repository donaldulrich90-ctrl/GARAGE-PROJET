"""Tests du tableau de bord (cockpit) — exactitude financière + isolation."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clients.models import Client, Vehicle
from diagnostics.models import DiagnosticCode, DiagnosticReport
from insurance.models import Insurance
from inventory.models import Part
from invoicing.models import Invoice, Payment
from repair_orders.models import RepairOrder, RepairOrderTask
from technical_visits.models import TechnicalVisit
from tenants.models import Garage
from workshops.models import WorkshopSection
from workshops.services import create_invoice_breakdown, create_payment_allocations

User = get_user_model()


def make_garage(name):
    return Garage.objects.create(name=name)


def make_admin(garage, username):
    u = User.objects.create_user(username=username, password="pw12345!")
    u.garage = garage
    u.role = User.ROLE_ADMIN
    u.save()
    return u


def make_section(garage, name, code, color="#3B82F6", order=1):
    return WorkshopSection.objects.create(
        garage=garage, name=name, code=code, color=color, display_order=order, is_active=True
    )


def make_vehicle(garage, plate="AA-111-BB"):
    client = Client.objects.create(garage=garage, full_name="Client Test", phone="70000000")
    return Vehicle.objects.create(garage=garage, client=client, plate_number=plate), client


def invoiced_order(garage, vehicle, client, section, labor, paid, status=RepairOrder.STATUS_IN_PROGRESS,
                   expected_at=None, done=True):
    """Crée un OR + tâche + facture (breakdown) + paiement (allocations)."""
    order = RepairOrder.objects.create(
        garage=garage, vehicle=vehicle, client=client, status=status, expected_at=expected_at,
    )
    RepairOrderTask.objects.create(
        repair_order=order, description="Intervention", section=section,
        cost=Decimal(labor), is_done=done,
    )
    invoice = Invoice.objects.create(garage=garage, repair_order=order, status=Invoice.STATUS_UNPAID)
    create_invoice_breakdown(invoice)
    if paid:
        payment = Payment.objects.create(invoice=invoice, amount=Decimal(paid))
        create_payment_allocations(payment)
    return order, invoice


class DashboardCockpitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.localdate()
        now = timezone.now()

        # ── Garage A (garage principal testé) ──────────────────────────────
        # NB : la création d'un Garage crée automatiquement les 4 sections par
        # défaut (signal post_save dans workshops.apps). On les réutilise.
        cls.garage_a = make_garage("Garage A")
        cls.user_a = make_admin(cls.garage_a, "admin_a")
        cls.mecanique = WorkshopSection.objects.get(garage=cls.garage_a, code="MECANIQUE")
        cls.electricite = WorkshopSection.objects.get(garage=cls.garage_a, code="ELECTRICITE")
        cls.vehicle_a, cls.client_a = make_vehicle(cls.garage_a, "AA-111-BB")

        # OR1 : en réparation, en retard, facturé 80 000, encaissé 50 000
        cls.order1, cls.invoice1 = invoiced_order(
            cls.garage_a, cls.vehicle_a, cls.client_a, cls.mecanique,
            labor=80000, paid=50000, status=RepairOrder.STATUS_IN_PROGRESS,
            expected_at=now - timedelta(days=1), done=True,
        )
        # OR2 : prêt, facturé 20 000 (électricité), non payé
        cls.order2, cls.invoice2 = invoiced_order(
            cls.garage_a, cls.vehicle_a, cls.client_a, cls.electricite,
            labor=20000, paid=0, status=RepairOrder.STATUS_READY, done=False,
        )
        # OR3 : livré aujourd'hui
        cls.order3 = RepairOrder.objects.create(
            garage=cls.garage_a, vehicle=cls.vehicle_a, client=cls.client_a,
            status=RepairOrder.STATUS_DELIVERED, delivered_at=now,
        )

        # Diagnostic récent (2 DTC)
        diag = DiagnosticReport.objects.create(
            garage=cls.garage_a, repair_order=cls.order1, scan_date=now, technician=cls.user_a,
        )
        DiagnosticCode.objects.create(diagnostic_report=diag, code="P0300")
        DiagnosticCode.objects.create(diagnostic_report=diag, code="P0420")

        # Stock faible (1 pièce sous le seuil)
        Part.objects.create(garage=cls.garage_a, reference="F-1", name="Filtre",
                            quantity_in_stock=1, alert_threshold=2)
        Part.objects.create(garage=cls.garage_a, reference="F-2", name="Bougie",
                            quantity_in_stock=10, alert_threshold=2)  # OK

        # Assurance qui expire bientôt + VT expirée
        Insurance.objects.create(
            garage=cls.garage_a, vehicle=cls.vehicle_a, insurance_company="AXA",
            policy_number="P1", start_date=cls.today - timedelta(days=300),
            end_date=cls.today + timedelta(days=10),
        )
        TechnicalVisit.objects.create(
            garage=cls.garage_a, vehicle=cls.vehicle_a, visit_date=cls.today - timedelta(days=400),
            expiry_date=cls.today - timedelta(days=5), inspection_center="CCVA",
        )

        # ── Garage B (pour tester l'isolation) ─────────────────────────────
        cls.garage_b = make_garage("Garage B")
        cls.user_b = make_admin(cls.garage_b, "admin_b")
        sec_b = WorkshopSection.objects.get(garage=cls.garage_b, code="MECANIQUE")
        veh_b, cli_b = make_vehicle(cls.garage_b, "BB-222-CC")
        invoiced_order(cls.garage_b, veh_b, cli_b, sec_b, labor=999000, paid=999000,
                       status=RepairOrder.STATUS_IN_PROGRESS)
        Part.objects.create(garage=cls.garage_b, reference="X", name="X",
                            quantity_in_stock=0, alert_threshold=5)

    def get_ctx(self, user):
        self.client.force_login(user)
        resp = self.client.get(reverse("dashboard_home"))
        self.assertEqual(resp.status_code, 200)
        return resp

    # ── KPIs financiers ────────────────────────────────────────────────────
    def test_production_du_jour(self):
        ctx = self.get_ctx(self.user_a).context
        # 80 000 (OR1) + 20 000 (OR2) — uniquement garage A
        self.assertEqual(ctx["production_jour"], Decimal("100000"))

    def test_encaisse_aujourdhui(self):
        ctx = self.get_ctx(self.user_a).context
        self.assertEqual(ctx["encaisse_jour"], Decimal("50000"))

    def test_reste_a_encaisser(self):
        ctx = self.get_ctx(self.user_a).context
        # (80 000 + 20 000) facturé non soldé - 50 000 payé = 50 000
        self.assertEqual(ctx["reste_global"], Decimal("50000"))
        self.assertEqual(ctx["unpaid_invoices_count"], 2)

    def test_production_nest_pas_encaissement(self):
        ctx = self.get_ctx(self.user_a).context
        self.assertNotEqual(ctx["production_jour"], ctx["encaisse_jour"])

    # ── Comptages atelier ──────────────────────────────────────────────────
    def test_vehicules_atelier_et_prets(self):
        ctx = self.get_ctx(self.user_a).context
        self.assertEqual(ctx["vehicles_atelier"], 2)   # OR1 + OR2 (pas OR3 livré)
        self.assertEqual(ctx["vehicles_prets"], 1)     # OR2

    def test_or_en_retard(self):
        ctx = self.get_ctx(self.user_a).context
        self.assertEqual(ctx["or_en_retard"], 1)       # OR1

    def test_workflow_steps(self):
        ctx = self.get_ctx(self.user_a).context
        wf = {s["key"]: s["count"] for s in ctx["workflow_steps"]}
        self.assertEqual(wf["reparation"], 1)
        self.assertEqual(wf["pret"], 1)
        self.assertEqual(wf["reception"], 0)
        self.assertEqual(ctx["delivered_today"], 1)

    # ── Sections ───────────────────────────────────────────────────────────
    def test_production_par_section(self):
        ctx = self.get_ctx(self.user_a).context
        by_name = {c["section"].name: c for c in ctx["section_cards"]}
        self.assertEqual(by_name["Mécanique"]["production"], Decimal("80000"))
        self.assertEqual(by_name["Mécanique"]["encaisse"], Decimal("50000"))
        self.assertEqual(by_name["Électricité automobile"]["production"], Decimal("20000"))
        # Les 4 sections par défaut apparaissent, même celles sans activité (0)
        self.assertEqual(len(ctx["section_cards"]), 4)
        self.assertEqual(by_name["Froid & Climatisation"]["production"], Decimal("0"))

    def test_classement_sections_ordonne(self):
        ctx = self.get_ctx(self.user_a).context
        prods = [k["production"] for k in ctx["section_kpis"]]
        self.assertEqual(prods, sorted(prods, reverse=True))
        self.assertEqual(ctx["section_kpis"][0]["section"].name, "Mécanique")

    # ── Diagnostics, stock, alertes ────────────────────────────────────────
    def test_diagnostics_recents(self):
        ctx = self.get_ctx(self.user_a).context
        diags = list(ctx["recent_diagnostics"])
        self.assertEqual(len(diags), 1)
        self.assertEqual(diags[0].codes_count, 2)

    def test_stock_faible(self):
        ctx = self.get_ctx(self.user_a).context
        self.assertEqual(ctx["low_stock_count"], 1)

    def test_alertes_assurance_vt(self):
        ctx = self.get_ctx(self.user_a).context
        self.assertEqual(ctx["ins_expiring"], 1)
        self.assertEqual(ctx["vt_expired"], 1)

    # ── Progression OR ─────────────────────────────────────────────────────
    def test_progression_or(self):
        ctx = self.get_ctx(self.user_a).context
        order1 = next(o for o in ctx["open_orders"] if o.pk == self.order1.pk)
        # 1 tâche terminée / 1 tâche => 100 %
        self.assertEqual(order1.progress_pct, 100)
        self.assertEqual(order1.amount_total, Decimal("80000"))
        order2 = next(o for o in ctx["open_orders"] if o.pk == self.order2.pk)
        self.assertEqual(order2.progress_pct, 0)  # tâche non terminée

    # ── Isolation multi-garage ─────────────────────────────────────────────
    def test_isolation_multi_garage(self):
        ctx = self.get_ctx(self.user_a).context
        # Aucune donnée du garage B (999 000) ne doit fuiter
        self.assertEqual(ctx["production_jour"], Decimal("100000"))
        self.assertEqual(ctx["encaisse_jour"], Decimal("50000"))
        self.assertEqual(ctx["low_stock_count"], 1)
        self.assertEqual(ctx["vehicles_atelier"], 2)

    def test_garage_b_voit_ses_propres_donnees(self):
        ctx = self.get_ctx(self.user_b).context
        self.assertEqual(ctx["production_jour"], Decimal("999000"))
        self.assertEqual(ctx["low_stock_count"], 1)

    # ── Sélecteur de période du graphique ──────────────────────────────────
    def test_chart_period_selector(self):
        self.client.force_login(self.user_a)
        for key in ("7", "30", "90", "year", "invalide"):
            resp = self.client.get(reverse("dashboard_home"), {"g": key})
            self.assertEqual(resp.status_code, 200)
        # valeur invalide => retombe sur le défaut
        self.assertEqual(resp.context["chart_period"], "30")

    # ── Rendu avec zéro donnée ─────────────────────────────────────────────
    def test_dashboard_zero_donnee(self):
        garage_c = make_garage("Garage C")
        user_c = make_admin(garage_c, "admin_c")
        resp = self.get_ctx(user_c)
        self.assertEqual(resp.context["production_jour"], Decimal("0"))
        self.assertEqual(resp.context["reste_global"], Decimal("0"))
        self.assertEqual(resp.context["vehicles_atelier"], 0)
        self.assertContains(resp, "Tableau de bord")
