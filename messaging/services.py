import re
import urllib.parse

# Templates système définis statiquement (non modifiables)
SYSTEM_TEMPLATES = [
    {
        'key': 'vehicule_pret',
        'name': 'Véhicule prêt',
        'body': (
            'Bonjour {prenom}, votre véhicule {immatriculation} ({marque} {modele}) est prêt. '
            'Vous pouvez venir le récupérer. — {nom_garage} ({telephone_garage})'
        ),
    },
    {
        'key': 'intervention',
        'name': 'Intervention nécessaire',
        'body': (
            'Bonjour {prenom}, votre véhicule {immatriculation} ({marque} {modele}) '
            'nécessite une intervention supplémentaire. '
            'Contactez-nous pour plus de détails. — {nom_garage} ({telephone_garage})'
        ),
    },
    {
        'key': 'rappel_rdv',
        'name': 'Rappel rendez-vous',
        'body': (
            'Bonjour {prenom}, nous vous rappelons votre rendez-vous au garage {nom_garage}. '
            'Contactez-nous au {telephone_garage} pour toute question.'
        ),
    },
    {
        'key': 'devis_dispo',
        'name': 'Devis disponible',
        'body': (
            'Bonjour {prenom}, votre devis pour le véhicule {immatriculation} est disponible. '
            'Contactez-nous au {telephone_garage} pour le consulter. — {nom_garage}'
        ),
    },
    {
        'key': 'rappel_assurance_30',
        'name': 'Rappel assurance J-30',
        'body': (
            'Bonjour {prenom}, votre assurance pour le véhicule {immatriculation} ({marque} {modele}) '
            'expire dans 30 jours le {date_expiration_assurance}. '
            'Anticipez le renouvellement ! — {nom_garage} ({telephone_garage})'
        ),
    },
    {
        'key': 'rappel_assurance_7',
        'name': 'Rappel assurance J-7',
        'body': (
            'Bonjour {prenom}, votre assurance pour le véhicule {immatriculation} ({marque} {modele}) '
            'expire dans 7 jours le {date_expiration_assurance}. '
            'Renouvelez rapidement ! — {nom_garage} ({telephone_garage})'
        ),
    },
    {
        'key': 'rappel_assurance_1',
        'name': 'Rappel assurance J-1',
        'body': (
            'Bonjour {prenom}, ⚠️ votre assurance pour le véhicule {immatriculation} '
            'expire DEMAIN le {date_expiration_assurance}. '
            'Renouvelez aujourd\'hui ! — {nom_garage} ({telephone_garage})'
        ),
    },
    {
        'key': 'rappel_vt_30',
        'name': 'Rappel visite technique J-30',
        'body': (
            'Bonjour {prenom}, la visite technique de votre véhicule {immatriculation} ({marque} {modele}) '
            'expire dans 30 jours le {date_expiration_vt}. '
            'Pensez à la programmer ! — {nom_garage} ({telephone_garage})'
        ),
    },
    {
        'key': 'rappel_vt_7',
        'name': 'Rappel visite technique J-7',
        'body': (
            'Bonjour {prenom}, la visite technique de votre véhicule {immatriculation} ({marque} {modele}) '
            'expire dans 7 jours le {date_expiration_vt}. '
            'Prenez rendez-vous rapidement ! — {nom_garage} ({telephone_garage})'
        ),
    },
    {
        'key': 'rappel_vt_1',
        'name': 'Rappel visite technique J-1',
        'body': (
            'Bonjour {prenom}, ⚠️ la visite technique de votre véhicule {immatriculation} '
            'expire DEMAIN le {date_expiration_vt}. '
            'Passez la visite aujourd\'hui ! — {nom_garage} ({telephone_garage})'
        ),
    },
]

# Les 4 premiers affichés dans le modal d'envoi individuel
QUICK_TEMPLATES = SYSTEM_TEMPLATES[:4]


def render_template(body: str, client, garage, vehicle=None) -> str:
    """Substitue les variables {variable} dans un corps de message."""
    parts = client.full_name.split(' ', 1)
    prenom = parts[0]
    nom = parts[1] if len(parts) > 1 else parts[0]

    ctx = {
        'prenom': prenom,
        'nom': nom,
        'nom_garage': garage.name,
        'telephone_garage': garage.phone or garage.whatsapp_number or '',
    }

    if vehicle:
        insurance = ''
        vt = ''
        if getattr(vehicle, 'insurance_expiry', None):
            insurance = vehicle.insurance_expiry.strftime('%d/%m/%Y')
        if getattr(vehicle, 'technical_visit_expiry', None):
            vt = vehicle.technical_visit_expiry.strftime('%d/%m/%Y')
        ctx.update({
            'immatriculation': vehicle.plate_number,
            'marque': vehicle.make,
            'modele': vehicle.model,
            'date_expiration_assurance': insurance,
            'date_expiration_vt': vt,
        })
    else:
        ctx.update({
            'immatriculation': '',
            'marque': '',
            'modele': '',
            'date_expiration_assurance': '',
            'date_expiration_vt': '',
        })

    result = body
    for key, value in ctx.items():
        result = result.replace('{' + key + '}', str(value))
    return result


def clean_phone(phone: str) -> str:
    """Nettoie un numéro de téléphone pour l'URL wa.me (chiffres seulement).
    Si le résultat est 8 chiffres (format local BF), préfixe l'indicatif 226."""
    digits = re.sub(r'[\s\-\+\(\)\.]', '', phone)
    if len(digits) == 8:
        digits = '226' + digits
    return digits


def build_wame_url(phone: str, message: str) -> str:
    """Construit un lien wa.me avec le message pré-rempli."""
    phone = clean_phone(phone)
    return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"
