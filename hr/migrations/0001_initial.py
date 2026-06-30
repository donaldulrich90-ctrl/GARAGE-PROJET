from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("expenses", "0001_initial"),
        ("tenants", "0002_garage_logo"),
    ]

    operations = [
        migrations.CreateModel(
            name="Employee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("first_name", models.CharField(max_length=100, verbose_name="Prénom")),
                ("last_name", models.CharField(max_length=100, verbose_name="Nom")),
                ("post", models.CharField(max_length=100, verbose_name="Poste")),
                ("employee_type", models.CharField(choices=[("employe", "Employé"), ("stagiaire", "Stagiaire")], default="employe", max_length=20, verbose_name="Type")),
                ("phone", models.CharField(blank=True, max_length=30, verbose_name="Téléphone")),
                ("start_date", models.DateField(verbose_name="Date d'entrée")),
                ("monthly_pay", models.DecimalField(decimal_places=0, max_digits=12, verbose_name="Salaire / Indemnité mensuel (FCFA)")),
                ("is_active", models.BooleanField(default=True, verbose_name="Actif")),
                ("notes", models.TextField(blank=True, verbose_name="Notes")),
                ("garage", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="employees", to="tenants.garage")),
            ],
            options={"ordering": ["last_name", "first_name"], "verbose_name": "Employé / Stagiaire", "abstract": False},
        ),
        migrations.CreateModel(
            name="Payroll",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reference", models.CharField(editable=False, max_length=20, unique=True)),
                ("month", models.DateField(verbose_name="Mois (1er du mois)")),
                ("amount", models.DecimalField(decimal_places=0, max_digits=12, verbose_name="Montant payé (FCFA)")),
                ("notes", models.TextField(blank=True, verbose_name="Notes")),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payrolls", to="hr.employee", verbose_name="Employé")),
                ("expense", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="payroll_entry", to="expenses.expense")),
                ("garage", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payrolls", to="tenants.garage")),
            ],
            options={"ordering": ["-month"], "verbose_name": "Bulletin de paie", "abstract": False},
        ),
        migrations.AlterUniqueTogether(
            name="payroll",
            unique_together={("employee", "month")},
        ),
    ]
