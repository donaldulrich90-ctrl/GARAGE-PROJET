"""
Renumérote les tokens du tableau à clés (key_token) pour tous les véhicules
actuellement au garage, dans l'ordre d'arrivée.

Utile après l'ajout du champ key_token, ou pour "remettre à zéro" la
numérotation du tableau à clés (les places libérées sont recompactées).

Exemples :
    python manage.py renumber_keys              # renumérote tous les garages
    python manage.py renumber_keys --garage 3   # un seul garage
    python manage.py renumber_keys --dry-run    # simulation, aucune écriture
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from clients.models import Vehicle
from tenants.models import Garage


class Command(BaseCommand):
    help = "Renumérote key_token 1..N par ordre d'arrivée pour les véhicules au garage."

    def add_arguments(self, parser):
        parser.add_argument("--garage", type=int, default=None,
                            help="PK du garage à traiter (par défaut: tous).")
        parser.add_argument("--dry-run", action="store_true",
                            help="N'écrit rien, affiche seulement les changements.")

    def handle(self, *args, **opts):
        garages = Garage.objects.all()
        if opts["garage"]:
            garages = garages.filter(pk=opts["garage"])

        total_changed = 0
        for garage in garages:
            self.stdout.write(self.style.MIGRATE_HEADING(f"[Garage {garage.pk}] {garage.name}"))
            # Ordre d'arrivée : arrival_number si présent, sinon created_at
            vehicles = list(
                Vehicle.objects.for_garage(garage)
                .filter(is_in_garage=True)
                .order_by("arrival_number", "created_at", "pk")
            )
            if not vehicles:
                self.stdout.write("  (aucun véhicule au garage)")
                continue

            changed = 0
            with transaction.atomic():
                # Passe 1 : mettre tous les tokens à NULL pour éviter les collisions d'unicité
                if not opts["dry_run"]:
                    Vehicle.objects.for_garage(garage).filter(
                        is_in_garage=True, key_token__isnull=False,
                    ).update(key_token=None)

                # Passe 2 : réassigner 1..N
                for new_token, v in enumerate(vehicles, start=1):
                    old = v.key_token
                    if old != new_token:
                        changed += 1
                        marker = " (modifié)" if not opts["dry_run"] else " (simulé)"
                    else:
                        marker = ""
                    self.stdout.write(
                        f"  #{new_token:>3}  {v.plate_number:<15}  {v.make} {v.model} "
                        f"(ancien: {old}){marker}"
                    )
                    if not opts["dry_run"]:
                        Vehicle.objects.filter(pk=v.pk).update(key_token=new_token)

            total_changed += changed
            self.stdout.write(self.style.SUCCESS(
                f"  → {len(vehicles)} véhicule(s), {changed} numéro(s) modifié(s)."
            ))

        verb = "auraient été" if opts["dry_run"] else "ont été"
        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé : {total_changed} token(s) {verb} modifié(s)."
        ))
