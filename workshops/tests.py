from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from accounts.models import User
from clients.models import Client, Vehicle
from invoicing.models import Invoice, InvoiceSectionBreakdown, PaymentSectionAllocation, Payment
from repair_orders.models import RepairOrder, RepairOrderPart, RepairOrderTask
from tenants.models import Garage
from workshops.models import WorkshopSection
from workshops.services import (
    create_invoice_breakdown,
    create_payment_allocations,
    get_order_section_breakdown,
)


def make_garage(name='Garage Test'):
    return Garage.objects.create(name=name, slug=name.lower().replace(' ', '-'))


def make_section(garage, code='MECA', name='Mécanique', color='#3B82F6'):
    return WorkshopSection.objects.get_or_create(
        garage=garage, code=code,
        defaults={'name': name, 'color': color, 'display_order': 1}
    )[0]


def make_client(garage):
    return Client.objects.create(garage=garage, full_name='Client Test', phone='0600000000')


def make_vehicle(garage, client):
    return Vehicle.objects.create(garage=garage, client=client, plate_number='AA-001-BB')


def make_order(garage, vehicle, client):
    return RepairOrder.objects.create(garage=garage, vehicle=vehicle, client=client)


class SectionIsolationTest(TestCase):
    def setUp(self):
        self.g1 = make_garage('Garage A')
        self.g2 = make_garage('Garage B')
        self.s1 = make_section(self.g1, 'MECA', 'Mécanique')
        self.s2 = make_section(self.g2, 'MECA', 'Mécanique')

    def test_isolation_between_garages(self):
        qs1 = WorkshopSection.objects.for_garage(self.g1)
        self.assertIn(self.s1, qs1)
        self.assertNotIn(self.s2, qs1)

    def test_same_code_in_different_garages_allowed(self):
        self.assertEqual(self.s1.code, self.s2.code)

    def test_duplicate_code_in_same_garage_raises(self):
        with self.assertRaises(IntegrityError):
            WorkshopSection.objects.create(
                garage=self.g1, code='MECA', name='Duplicate',
            )


class TaskWithSectionTest(TestCase):
    def setUp(self):
        self.g = make_garage()
        self.s = make_section(self.g)
        self.c = make_client(self.g)
        self.v = make_vehicle(self.g, self.c)
        self.order = make_order(self.g, self.v, self.c)

    def test_add_task_with_section(self):
        task = RepairOrderTask.objects.create(
            repair_order=self.order,
            description='Vidange moteur',
            section=self.s,
            cost=Decimal('15000'),
        )
        self.assertEqual(task.section, self.s)
        self.assertEqual(self.order.total_labor, Decimal('15000'))

    def test_task_section_total(self):
        RepairOrderTask.objects.create(repair_order=self.order, description='T1', section=self.s, cost=Decimal('10000'))
        RepairOrderTask.objects.create(repair_order=self.order, description='T2', section=self.s, cost=Decimal('20000'))
        breakdown = get_order_section_breakdown(self.order)
        self.assertEqual(breakdown[self.s.pk]['labor'], Decimal('30000'))


class PartWithSectionTest(TestCase):
    def setUp(self):
        self.g = make_garage()
        self.s = make_section(self.g)
        self.c = make_client(self.g)
        self.v = make_vehicle(self.g, self.c)
        self.order = make_order(self.g, self.v, self.c)
        from inventory.models import Part
        self.part = Part.objects.create(
            garage=self.g, name='Filtre', reference='F001',
            unit_price=Decimal('5000'), quantity_in_stock=10,
        )

    def test_add_part_with_section(self):
        op = RepairOrderPart.objects.create(
            repair_order=self.order, part=self.part,
            quantity=2, unit_price=Decimal('5000'), section=self.s,
        )
        self.assertEqual(op.section, self.s)
        self.assertEqual(op.line_total, Decimal('10000'))

    def test_part_section_total(self):
        RepairOrderPart.objects.create(repair_order=self.order, part=self.part, quantity=2, unit_price=Decimal('5000'), section=self.s)
        breakdown = get_order_section_breakdown(self.order)
        self.assertEqual(breakdown[self.s.pk]['parts'], Decimal('10000'))


class OrderTotalTest(TestCase):
    def setUp(self):
        self.g = make_garage()
        self.s1 = make_section(self.g, 'MECA', 'Mécanique')
        self.s2 = make_section(self.g, 'ELEC', 'Électricité')
        self.c = make_client(self.g)
        self.v = make_vehicle(self.g, self.c)
        self.order = make_order(self.g, self.v, self.c)

    def test_total_or_is_sum_of_sections(self):
        RepairOrderTask.objects.create(repair_order=self.order, description='T1', section=self.s1, cost=Decimal('50000'))
        RepairOrderTask.objects.create(repair_order=self.order, description='T2', section=self.s2, cost=Decimal('30000'))
        breakdown = get_order_section_breakdown(self.order)
        total_from_sections = sum(v['total'] for v in breakdown.values())
        self.assertEqual(total_from_sections, self.order.total_cost)


class InvoiceBreakdownTest(TestCase):
    def setUp(self):
        self.g = make_garage()
        self.s1 = make_section(self.g, 'MECA', 'Mécanique')
        self.s2 = make_section(self.g, 'ELEC', 'Électricité')
        self.c = make_client(self.g)
        self.v = make_vehicle(self.g, self.c)
        self.order = make_order(self.g, self.v, self.c)
        RepairOrderTask.objects.create(repair_order=self.order, description='T1', section=self.s1, cost=Decimal('100000'))
        RepairOrderTask.objects.create(repair_order=self.order, description='T2', section=self.s2, cost=Decimal('60000'))
        self.invoice = Invoice.objects.create(garage=self.g, repair_order=self.order)

    def test_create_breakdown_creates_records(self):
        create_invoice_breakdown(self.invoice)
        bds = InvoiceSectionBreakdown.objects.filter(invoice=self.invoice)
        self.assertEqual(bds.count(), 2)

    def test_sum_of_sections_equals_invoice_total(self):
        create_invoice_breakdown(self.invoice)
        total_bd = sum(bd.total_amount for bd in InvoiceSectionBreakdown.objects.filter(invoice=self.invoice))
        self.invoice.refresh_from_db()
        self.assertEqual(total_bd, self.invoice.total_snapshot)
        self.assertEqual(total_bd, self.order.total_cost)


class PaymentAllocationTest(TestCase):
    def setUp(self):
        self.g = make_garage()
        self.s1 = make_section(self.g, 'MECA', 'Mécanique')
        self.s2 = make_section(self.g, 'ELEC', 'Électricité')
        self.s3 = make_section(self.g, 'CLIM', 'Climatisation')
        self.c = make_client(self.g)
        self.v = make_vehicle(self.g, self.c)
        self.order = make_order(self.g, self.v, self.c)
        RepairOrderTask.objects.create(repair_order=self.order, description='T1', section=self.s1, cost=Decimal('100000'))
        RepairOrderTask.objects.create(repair_order=self.order, description='T2', section=self.s2, cost=Decimal('60000'))
        RepairOrderTask.objects.create(repair_order=self.order, description='T3', section=self.s3, cost=Decimal('40000'))
        self.invoice = Invoice.objects.create(garage=self.g, repair_order=self.order)
        create_invoice_breakdown(self.invoice)

    def test_full_payment_allocations_sum_to_payment(self):
        payment = Payment.objects.create(invoice=self.invoice, amount=Decimal('200000'), method='cash')
        create_payment_allocations(payment)
        allocs = PaymentSectionAllocation.objects.filter(payment=payment)
        self.assertEqual(allocs.count(), 3)
        total_alloc = sum(a.amount for a in allocs)
        self.assertEqual(total_alloc, Decimal('200000'))

    def test_partial_payment_allocations_sum_exactly(self):
        payment = Payment.objects.create(invoice=self.invoice, amount=Decimal('100000'), method='cash')
        create_payment_allocations(payment)
        allocs = PaymentSectionAllocation.objects.filter(payment=payment)
        total_alloc = sum(a.amount for a in allocs)
        self.assertEqual(total_alloc, Decimal('100000'))

    def test_proportional_allocation_is_correct(self):
        payment = Payment.objects.create(invoice=self.invoice, amount=Decimal('100000'), method='cash')
        create_payment_allocations(payment)
        allocs = {a.section_id: a.amount for a in PaymentSectionAllocation.objects.filter(payment=payment)}
        # s1 = 100k/200k = 50000, s2 = 60k/200k = 30000, s3 = 40k/200k = 20000
        self.assertEqual(allocs[self.s1.pk], Decimal('50000.00'))
        self.assertEqual(allocs[self.s2.pk], Decimal('30000.00'))
        self.assertEqual(allocs[self.s3.pk], Decimal('20000.00'))

    def test_decimal_rounding_no_drift(self):
        payment = Payment.objects.create(invoice=self.invoice, amount=Decimal('99999.99'), method='cash')
        create_payment_allocations(payment)
        total = sum(a.amount for a in PaymentSectionAllocation.objects.filter(payment=payment))
        self.assertEqual(total, Decimal('99999.99'))

    def test_single_section_invoice_full_allocation(self):
        g = make_garage('Solo')
        s = make_section(g, 'SOLO', 'Solo')
        c = make_client(g)
        v = make_vehicle(g, c)
        order = make_order(g, v, c)
        RepairOrderTask.objects.create(repair_order=order, description='T', section=s, cost=Decimal('50000'))
        inv = Invoice.objects.create(garage=g, repair_order=order)
        create_invoice_breakdown(inv)
        pay = Payment.objects.create(invoice=inv, amount=Decimal('50000'), method='cash')
        create_payment_allocations(pay)
        alloc = PaymentSectionAllocation.objects.get(payment=pay)
        self.assertEqual(alloc.section, s)
        self.assertEqual(alloc.amount, Decimal('50000'))


class KpiReportTest(TestCase):
    def setUp(self):
        self.g = make_garage()
        self.s = make_section(self.g)
        self.c = make_client(self.g)
        self.v = make_vehicle(self.g, self.c)
        self.order = make_order(self.g, self.v, self.c)
        RepairOrderTask.objects.create(repair_order=self.order, description='T', section=self.s, cost=Decimal('100000'))
        self.invoice = Invoice.objects.create(garage=self.g, repair_order=self.order)
        create_invoice_breakdown(self.invoice)
        self.payment = Payment.objects.create(invoice=self.invoice, amount=Decimal('80000'), method='cash')
        create_payment_allocations(self.payment)

    def _kpis(self, start=None, end=None):
        from workshops.services import get_section_kpis
        from django.utils import timezone
        if not start:
            start = timezone.now().date().replace(day=1)
        if not end:
            end = timezone.now().date()
        return get_section_kpis(self.g, start_date=start, end_date=end)

    def test_kpi_includes_production_and_encaisse(self):
        kpis = self._kpis()
        self.assertTrue(len(kpis) > 0)
        kpi = kpis[0]
        self.assertEqual(kpi['production'], Decimal('100000'))
        self.assertEqual(kpi['encaisse'], Decimal('80000'))
        self.assertEqual(kpi['reste'], Decimal('20000'))


class DiagnosticTest(TestCase):
    def setUp(self):
        from diagnostics.models import DiagnosticReport, DiagnosticCode
        self.g = make_garage()
        self.c = make_client(self.g)
        self.v = make_vehicle(self.g, self.c)
        self.order = make_order(self.g, self.v, self.c)
        from django.utils import timezone
        self.report = DiagnosticReport.objects.create(
            garage=self.g, repair_order=self.order,
            scan_date=timezone.now(),
        )
        DiagnosticCode.objects.create(
            diagnostic_report=self.report, code='P0301',
            module_system='PCM', description='Raté allumage', status='present',
        )
        DiagnosticCode.objects.create(
            diagnostic_report=self.report, code='P0420',
            module_system='PCM', description='Catalyseur', status='history',
        )

    def test_dtc_count(self):
        self.assertEqual(self.report.dtc_count, 2)

    def test_vehicle_link(self):
        self.assertEqual(self.report.vehicle, self.v)

    def test_diagnostic_isolation(self):
        from diagnostics.models import DiagnosticReport
        g2 = make_garage('Other')
        qs = DiagnosticReport.objects.for_garage(g2)
        self.assertEqual(qs.count(), 0)
        qs1 = DiagnosticReport.objects.for_garage(self.g)
        self.assertEqual(qs1.count(), 1)

    def test_multiple_dtc_codes(self):
        from diagnostics.models import DiagnosticCode
        codes = list(DiagnosticCode.objects.filter(diagnostic_report=self.report))
        self.assertEqual(len(codes), 2)
        codes_list = [c.code for c in codes]
        self.assertIn('P0301', codes_list)
        self.assertIn('P0420', codes_list)
