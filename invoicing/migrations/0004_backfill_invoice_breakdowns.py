from django.db import migrations


def backfill_breakdowns(apps, schema_editor):
    Invoice = apps.get_model('invoicing', 'Invoice')
    InvoiceSectionBreakdown = apps.get_model('invoicing', 'InvoiceSectionBreakdown')
    RepairOrderTask = apps.get_model('repair_orders', 'RepairOrderTask')
    RepairOrderPart = apps.get_model('repair_orders', 'RepairOrderPart')
    from decimal import Decimal

    for invoice in Invoice.objects.select_related('repair_order').all():
        if InvoiceSectionBreakdown.objects.filter(invoice=invoice).exists():
            continue
        ro = invoice.repair_order
        if ro is None:
            continue

        # Group tasks by section
        section_data = {}

        for task in RepairOrderTask.objects.filter(repair_order=ro).select_related('section'):
            key = task.section_id
            if key not in section_data:
                section_data[key] = {'section_id': key, 'labor': Decimal('0'), 'parts': Decimal('0')}
            section_data[key]['labor'] += task.cost or Decimal('0')

        for op in RepairOrderPart.objects.filter(repair_order=ro).select_related('section'):
            key = op.section_id
            if key not in section_data:
                section_data[key] = {'section_id': key, 'labor': Decimal('0'), 'parts': Decimal('0')}
            qty = op.quantity or 0
            price = op.unit_price or Decimal('0')
            section_data[key]['parts'] += qty * price

        if not section_data:
            # OR has no tasks/parts — create a null section entry with zero totals
            InvoiceSectionBreakdown.objects.create(
                invoice=invoice,
                section_id=None,
                labor_amount=Decimal('0'),
                parts_amount=Decimal('0'),
                total_amount=Decimal('0'),
            )
            Invoice.objects.filter(pk=invoice.pk).update(total_snapshot=Decimal('0'))
            continue

        total = Decimal('0')
        for key, data in section_data.items():
            t = data['labor'] + data['parts']
            InvoiceSectionBreakdown.objects.create(
                invoice=invoice,
                section_id=data['section_id'],
                labor_amount=data['labor'],
                parts_amount=data['parts'],
                total_amount=t,
            )
            total += t

        Invoice.objects.filter(pk=invoice.pk).update(total_snapshot=total)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing', '0003_invoice_section_breakdown'),
        ('repair_orders', '0002_add_section_to_task_and_part'),
    ]

    operations = [
        migrations.RunPython(backfill_breakdowns, noop),
    ]
