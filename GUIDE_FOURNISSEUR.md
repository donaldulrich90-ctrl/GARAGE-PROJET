# Guide de l'espace fournisseur

Cette version conserve les fonctions existantes du garage et ajoute un espace
réservé à chaque fournisseur.

## Langues disponibles

L'interface propose **FR** et **EN** sur la page de connexion et dans le menu.
Le choix est mémorisé dans le navigateur. L'espace fournisseur, ses formulaires,
ses alertes, ses rapports et ses exports CSV sont disponibles en français et en
anglais. La navigation principale du garage est également bilingue.

## Mise à jour ou première installation

1. Sous Windows, double-cliquer sur `lancer.bat`.
2. Le lanceur installe les dépendances manquantes et applique les migrations.
3. La base existante est conservée. Les données de démonstration ne sont
   ajoutées que si aucune base `db.sqlite3` n'existe.

Avant toute mise à jour d'une installation en production, effectuer une copie
de sauvegarde de la base de données et du dossier `media`.

## Créer un fournisseur et son compte

1. Se connecter avec un compte **Administrateur garage**.
2. Ouvrir **Équipe et accès** (`/compte/equipe/`).
3. Choisir **Nouveau fournisseur**.
4. Saisir la raison sociale, le responsable, le téléphone, l'adresse,
   l'IFU/RCCM, le site web et le logo.
5. Définir l'identifiant et le mot de passe du compte fournisseur.

La fiche société et le compte de connexion sont créés ensemble. Le logo est
affiché dans le menu et le tableau de bord fournisseur.

## Fonctions disponibles pour le fournisseur

- **Tableau de bord** : stock total, valeur du stock, alertes, commandes et
  résultats du jour, de la semaine et du mois.
- **Mon stock** : prix, quantité disponible, G-CODE, référence interne, délai
  de livraison et seuil d'alerte propre à chaque pièce.
- **Mouvements** : entrées, sorties/ventes et ajustements d'inventaire.
- **Ventes détaillées** : référence de vente, client ou garage, pièce,
  quantité, prix, total et mode de paiement.
- **Dépenses** : date, catégorie, montant, paiement, référence, description et
  justificatif.
- **Rapports** : chiffre d'affaires, dépenses, résultat net, ventes par pièce,
  dépenses par catégorie et détail par jour.
- **Export Excel** : le bouton CSV du rapport produit un fichier compatible
  avec Excel.
- **Alertes internes** : un badge et un message apparaissent dans la plateforme
  quand une quantité atteint son seuil. Ces alertes ne sont pas envoyées sur
  WhatsApp.

## Contrôles intégrés

- Un fournisseur ne peut consulter ou modifier que ses propres données.
- Une vente supérieure au stock disponible est refusée.
- Les sorties issues d'une commande sont liées à cette commande et alimentent
  automatiquement le détail des ventes.
- Un garage désactivé bloque aussi les comptes fournisseurs qui lui sont liés.
- Les téléchargements CSV neutralisent les cellules pouvant exécuter une
  formule lors de l'ouverture dans un tableur.

## Vérification technique effectuée

- Installation complète des migrations sur une base neuve.
- Vérification de la configuration Django.
- Quatorze tests automatisés couvrant le compte fournisseur, les pages principales,
  les ventes, le stock, les dépenses, les rapports, l'isolation des données,
  l'export CSV, le changement de langue et le blocage des comptes désactivés.
