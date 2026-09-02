# Garage SaaS — Plateforme de gestion de garages (MVP)

ERP multi-tenant pour garages automobiles, construit sur le même modèle
architectural que GeDrilling (Django). Chaque garage client est un tenant
isolé par colonne `garage_id` (pas de schéma séparé par base de données).

## Modules inclus dans ce MVP

- **tenants** — modèle `Garage` (le tenant), plans d'abonnement, flag
  `faest_supplier_enabled` pour activer FAEST comme fournisseur intégré.
- **accounts** — utilisateur custom avec rôles (admin garage, réception,
  mécanicien, caissier, magasinier).
- **clients** — fiches clients + véhicules (immatriculation, kilométrage,
  historique via `vehicle.repair_orders`).
- **inventory** — fournisseurs (avec flag `is_faest`), pièces, stock,
  mouvements de stock, seuils d'alerte de réapprovisionnement.
- **supplier_portal** — espace fournisseur séparé : fiche société et logo,
  catalogue et stock, ventes détaillées, dépenses, commandes reçues, alertes
  de stock sur la plateforme et rapports journaliers, hebdomadaires et
  mensuels avec export CSV, disponible en français et en anglais.
- **repair_orders** — le cœur du système : ordre de réparation (OR) avec
  statut (reçu → diagnostic → en cours → prêt → livré), tâches de main
  d'œuvre, pièces consommées.
- **invoicing** — devis, factures, paiements (espèces / mobile money /
  virement), calcul automatique du solde dû.
- **dashboard** — vue garage (KPIs, alertes stock, factures impayées,
  derniers OR) + vue plateforme pour le staff (liste des garages actifs).
- **core** — `TenantModel` abstrait + `TenantManager.for_garage()` pour
  l'isolation des données, mixin `TenantScopedAdmin` qui filtre
  automatiquement l'admin Django par garage de l'utilisateur connecté.

## Démarrage rapide

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py shell < seed_demo.py   # données de démo
python manage.py runserver
```

Sous Windows, `lancer.bat` installe ou actualise les dépendances, applique les
migrations sans effacer la base existante, puis démarre l'application. Les
données de démonstration ne sont créées que lors de la première installation.

## Création et utilisation d'un compte fournisseur

Depuis **Utilisateurs > Nouveau fournisseur**, l'administrateur du garage
enregistre en une fois la société (raison sociale, responsable, téléphone,
adresse, IFU/RCCM, site, logo) et son compte de connexion. Le fournisseur
dispose ensuite de son propre tableau de bord et ne voit que ses données.

Son espace permet de :

- gérer ses références, quantités et seuils d'alerte ;
- enregistrer chaque entrée ou sortie de stock et les détails d'une vente ;
- suivre les dépenses avec justificatif ;
- consulter les commandes des garages ;
- comparer ventes, dépenses et résultat net par jour, semaine ou mois ;
- exporter le rapport en CSV ouvrable dans Excel.

Les alertes de stock du portail restent internes à la plateforme : aucun
message WhatsApp n'est envoyé pour ces alertes.

## Configuration de production

Les informations sensibles sont lues depuis l'environnement. Variables utiles :

- `DJANGO_SECRET_KEY` : clé secrète longue et aléatoire ;
- `DJANGO_DEBUG=False` ;
- `DJANGO_ALLOWED_HOSTS=garage.exemple.com,www.garage.exemple.com` ;
- `DJANGO_SECURE_SSL_REDIRECT=True` après activation de HTTPS ;
- `DJANGO_SECURE_HSTS_SECONDS=31536000` une fois HTTPS vérifié (activer HSTS
  progressivement et avec prudence) ;
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` et
  `POSTGRES_PORT` pour PostgreSQL ;
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://garage.exemple.com`.

Sans `POSTGRES_DB`, l'application utilise SQLite, ce qui convient au test local
mais pas à une production avec plusieurs utilisateurs simultanés.

Comptes de test créés par `seed_demo.py` :
- **Admin garage** : `admin_wayalghin` / `garage1234` → voit uniquement
  son garage (dashboard sur `/`, admin filtré sur `/admin/`).
- **Staff plateforme** : `platform_admin` / `platform1234` → superuser,
  voit tous les garages dans `/admin/`.

## Prochaines étapes suggérées

1. **Passage à PostgreSQL** en production (changer `DATABASES` dans
   `settings.py`) — SQLite ne convient qu'au dev/démo.
2. **API REST** (Django REST Framework) si une app mobile mécanicien ou
   un portail client en libre-service est envisagé plus tard.
3. **Notifications WhatsApp/SMS** (Celery + Redis pour l'asynchrone) :
   rappel de rendez-vous, notification "véhicule prêt".
4. **Génération PDF** des devis/factures (WeasyPrint ou équivalent).
5. **Intégration FAEST réelle** : quand `faest_supplier_enabled=True`,
   permettre aux garages de passer commande de pièces directement
   depuis l'interface, avec synchronisation du catalogue FAEST. C'est le
   levier qui transforme ce SaaS en canal de vente supplémentaire pour
   FAEST — à formaliser une fois les premiers garages pilotes validés.
6. **Facturation SaaS elle-même** (abonnement par garage) — intégration
   Mobile Money ou facturation manuelle au départ.
7. **Tests** avec 1-2 garages pilotes réels avant d'ajouter plus de
   modules (RH avancée, comptabilité complète, reporting BI).

## Notes d'architecture

- L'isolation multi-tenant est faite par colonne (`garage_id`), pas par
  schéma séparé. C'est plus simple à opérer pour une équipe réduite ; si
  un gros client exige une isolation physique stricte des données plus
  tard, cette décision peut être révisée pour ce client spécifique.
- Le superuser Django (`is_superuser=True`, `garage=None`) joue le rôle
  de staff plateforme et voit tout. Tout autre utilisateur est rattaché
  à exactement un garage.
