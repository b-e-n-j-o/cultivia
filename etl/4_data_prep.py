"""
Ce script est le composant central de préparation des données pour une application d'événements culturels. 
Il prend en entrée des données brutes d'événements au format JSON et les transforme en un format structuré 
et enrichi, prêt à être utilisé par le reste de l'application. Le script normalise les dates, les lieux et 
les prix, ajoute des identifiants uniques et des métadonnées supplémentaires, tout en assurant une gestion 
robuste des erreurs et une traçabilité complète via des logs détaillés.

Préparateur de données pour événements culturels
----------------------------------------------

1. Objectif principal :
- Transformation des données brutes d'événements en format structuré et normalisé

2. Traitement des données :
- Extraction et standardisation des informations essentielles (titre, date, lieu, prix)
- Conversion des dates en formats ISO et timestamp Unix
- Normalisation des coordonnées géographiques
- Génération d'identifiants uniques (UUID)
- Création de cartes d'événements formatées

3. Fonctionnalités de gestion :
- Journalisation détaillée des opérations
- Gestion des erreurs et exceptions
- Sauvegarde en format JSON structuré

4. Enrichissement des données :
- Ajout de métadonnées complémentaires
- Normalisation pour intégration avec d'autres services
- Gestion des informations sur les participants
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path
from tqdm import tqdm

class EventDataPreparator:
    def __init__(self):
        self.setup_logging()
        
    def setup_logging(self):
        custom_format = logging.Formatter(
            '%(asctime)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        logger.handlers = []
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(custom_format)
        logger.addHandler(console_handler)
        
        file_handler = logging.FileHandler('preparation.log')
        file_handler.setFormatter(custom_format)
        logger.addHandler(file_handler)

    def _generate_uuid(self) -> str:
        return str(uuid.uuid4())

    def _extract_location_info(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            meta_location = None
            for meta in event_data.get('meta_data', []):
                if '@type' in meta and meta['@type'] == 'Event':
                    meta_location = meta.get('location', {})
                    break

            if meta_location:
                address = meta_location.get('address', {})
                address_parts = [
                    address.get('streetAddress', ''),
                    address.get('addressLocality', ''),
                    address.get('addressRegion', ''),
                    address.get('postalCode', '')
                ]
                full_address = ', '.join(part for part in address_parts if part)

                geo = meta_location.get('geo', {})
                
                location_info = {
                    "name": meta_location.get('name'),
                    "address": full_address,
                    "latitude": geo.get('latitude'),
                    "longitude": geo.get('longitude')
                }
                return location_info
            else:
                lieu = event_data.get('lieu', {})
                return {
                    "name": lieu.get('nom'),
                    "address": lieu.get('adresse'),
                    "latitude": None,
                    "longitude": None
                }
        except Exception as e:
            logging.error(f"❌ Erreur extraction localisation: {e}")
            return {}

    def _extract_price(self, event_data: Dict[str, Any]) -> str:
        try:
            for meta in event_data.get('meta_data', []):
                if '@type' in meta and meta['@type'] == 'Event':
                    offers = meta.get('offers', {})
                    if offers.get('price') is not None:
                        price = f"{offers['price']} {offers.get('priceCurrency', 'CAD')}"
                        return price

            prix = event_data.get('prix', '')
            if prix.lower() == 'gratuit' or 'gratuit' in prix.lower():
                return "Gratuit"
            elif prix.lower() == 'billets':
                return "Non disponible"
            return prix
        except Exception as e:
            logging.error(f"❌ Erreur extraction prix: {e}")
            return ""

    def _extract_participants(self, event_data: Dict[str, Any]) -> tuple:
        performers = []
        organizers = []
        contributors = []

        try:
            for meta in event_data.get('meta_data', []):
                if '@type' in meta and meta['@type'] == 'Event':
                    performers = [perf['name'] for perf in meta.get('performer', []) if perf.get('name')]
                    organizers = [org['name'] for org in meta.get('organizer', []) if org.get('name')]
                    contributors = [cont['name'] for cont in meta.get('contributor', []) if cont.get('name')]

            return (
                ', '.join(performers) if performers else None,
                ', '.join(organizers) if organizers else None,
                ', '.join(contributors) if contributors else None
            )
        except Exception as e:
            logging.error(f"❌ Erreur extraction participants: {e}")
            return (None, None, None)

    def _convert_date_to_iso(self, date_str: str) -> Optional[str]:
        try:
            mois_mapping = {
                'janv.': '01', 'févr.': '02', 'mars': '03', 'avr.': '04',
                'mai': '05', 'juin': '06', 'juil.': '07', 'août': '08',
                'sept.': '09', 'oct.': '10', 'nov.': '11', 'déc.': '12'
            }
            
            parts = date_str.split()
            if len(parts) != 3:
                logging.warning("⚠️ Format de date invalide")
                return None
                
            jour = parts[0].zfill(2)
            mois = mois_mapping.get(parts[1], '01')
            annee = parts[2]
            
            date_iso = f"{annee}-{mois}-{jour}"
            return date_iso
        except Exception as e:
            logging.error(f"❌ Erreur conversion date: {e}")
            return None

    def _convert_to_unix_timestamp(self, date_iso: str) -> Optional[int]:
        """Convertit une date ISO en timestamp Unix"""
        try:
            if not date_iso:
                return None
            return int(datetime.fromisoformat(date_iso).timestamp())
        except Exception as e:
            logging.error(f"❌ Erreur conversion timestamp: {e}")
            return None

    def prepare_event_data(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        try:
            performer, organizer, contributor = self._extract_participants(raw_event)
            
            embedding_text = f"{raw_event.get('titre', '')} - {raw_event.get('description', '')}"

            event_url = None
            for meta in raw_event.get('meta_data', []):
                if '@type' in meta and meta['@type'] == 'Event':
                    offers = meta.get('offers', {})
                    event_url = offers.get('url')
                    if event_url:
                        logging.info("🔗 URL de l'événement trouvée")
                    break

            location_info = self._extract_location_info(raw_event)
            date_iso = self._convert_date_to_iso(raw_event.get('date', ''))
            date_unix = self._convert_to_unix_timestamp(date_iso) if date_iso else None

            event_card = f"""
ÉVÉNEMENT: {raw_event.get('titre', 'Non spécifié')}
DATE: {raw_event.get('date', 'Non spécifié')} à {raw_event.get('heure', 'Non spécifié')}
LIEU: {location_info.get('name', 'Non spécifié')}
ADRESSE: {location_info.get('address', 'Non spécifié')}
DISCIPLINE: {raw_event.get('discipline', 'Non spécifié')}
ARTISTES: {performer if performer else 'Non spécifié'}
DESCRIPTION: {raw_event.get('description', 'Non spécifié')}
BILLETS: {event_url if event_url else 'Non spécifié'}
"""

            prepared_event = {
                "uuid": self._generate_uuid(),
                "event_url": event_url,
                "title": raw_event.get('titre'),
                "description": raw_event.get('description'),
                "embedding_text": embedding_text,
                "discipline": raw_event.get('discipline'),
                "price": self._extract_price(raw_event),
                "date": raw_event.get('date'),
                "date_iso": date_iso,
                "date_unix": date_unix,
                "time": raw_event.get('heure'),
                "location": location_info,
                "performer": performer,
                "organizer": organizer,
                "contributor": contributor,
                "image_url": raw_event.get('image_url'),
                "ticket_url": raw_event.get('billetterie_url'),
                "source_url": raw_event.get('meta_data', [{}])[1].get('@id') if len(raw_event.get('meta_data', [])) > 1 else None,
                "event_card": event_card,
                "audience": raw_event.get('meta_data', [{}])[1].get('audience', [{}])[0].get('audienceType') if raw_event.get('meta_data') else None,
                "language": raw_event.get('meta_data', [{}])[1].get('inLanguage') if raw_event.get('meta_data') else None
            }

            logging.info("✅ Événement préparé avec succès")
            return prepared_event
        except Exception as e:
            logging.error(f"❌ Erreur préparation événement: {e}")
            return {}

    def process_events(self, input_file: str, output_file: str):
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                raw_events = json.load(f)

            if not isinstance(raw_events, list):
                raw_events = [raw_events]
                
            total_events = len(raw_events)
            logging.info(f"📊 {total_events} événements à traiter")

            prepared_events = []
            for event in tqdm(raw_events, desc="Traitement des événements", unit="événement"):
                prepared_event = self.prepare_event_data(event)
                if prepared_event:
                    prepared_events.append(prepared_event)

            prepared_data = {
                "events": prepared_events,
                "processing_date": datetime.now().isoformat()
            }

            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            logging.info(f"💾 Sauvegarde dans: {output_file}")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(prepared_data, f, ensure_ascii=False, indent=2)

            logging.info(f"✨ {len(prepared_events)}/{total_events} événements traités avec succès")

        except Exception as e:
            logging.error(f"❌ Erreur traitement fichier: {e}")

def main():
    logging.info("🎉 Démarrage du préparateur de données")
    today = datetime.now().strftime('%Y-%m-%d')
    
    input_file = f'../data/json_files/{today}.json'
    output_file = f'../data/json_prepared/{today}.json'
    
    preparator = EventDataPreparator()
    preparator.process_events(input_file, output_file)
    logging.info("🏁 Traitement terminé")

if __name__ == "__main__":
    main()



# Format d'entrée (données brutes) :
# {
#     "titre": "Concert de Jazz",
#     "date": "15 mars 2024",
#     "heure": "20h00",
#     "lieu": {
#         "nom": "Salle de spectacle",
#         "adresse": "123 rue principale"
#     },
#     "prix": "Gratuit",
#     "description": "Une soirée jazz exceptionnelle",
#     "meta_data": [
#         {
#             "@type": "Event",
#             "location": {
#                 "address": {
#                     "streetAddress": "123 rue principale",
#                     "addressLocality": "Montréal",
#                     "postalCode": "H2X 1Y2"
#                 },
#                 "geo": {
#                     "latitude": 45.5017,
#                     "longitude": -73.5673
#                 }
#             }
#         }
#     ]
# }

# Format de sortie (données structurées) :
# {
#     "events": [
#         {
#             "uuid": "550e8400-e29b-41d4-a716-446655440000",
#             "event_url": "https://...",
#             "title": "Concert de Jazz",
#             "description": "Une soirée jazz exceptionnelle",
#             "embedding_text": "Concert de Jazz - Une soirée jazz exceptionnelle",
#             "discipline": "Musique",
#             "price": "Gratuit",
#             "date": "15 mars 2024",
#             "date_iso": "2024-03-15",
#             "date_unix": 1710460800,
#             "time": "20h00",
#             "location": {
#                 "name": "Salle de spectacle",
#                 "address": "123 rue principale, Montréal, H2X 1Y2",
#                 "latitude": 45.5017,
#                 "longitude": -73.5673
#             },
#             "performer": "Artiste 1, Artiste 2",
#             "organizer": "Organisation culturelle",
#             "contributor": "Partenaire culturel",
#             "event_card": "ÉVÉNEMENT: Concert de Jazz\nDATE: 15 mars 2024 à 20h00\n...",
#             "language": "fr",
#             "audience": "Tout public"
#         }
#     ],
#     "processing_date": "2024-03-14T10:30:00"
# }

# Les avantages de cette structuration :
# Normalisation :
# Dates standardisées (ISO et Unix timestamp)
# Coordonnées géographiques uniformisées
# Format de prix cohérent
# Enrichissement :
# Ajout d'un UUID unique
# Création d'un texte pour l'embedding
# Génération d'une carte d'événement formatée
# Facilitation de l'utilisation :
# Structure cohérente pour tous les événements
# Données géolocalisées exploitables
# Recherche et filtrage simplifiés
# Intégration simplifiée :
# Format JSON standard
# Données prêtes pour une base de données
# Compatible avec les API REST
# Cette structuration permet une meilleure exploitation des données pour :
# L'affichage sur un site web
# La recherche géolocalisée
# Le filtrage par date/prix/catégorie
# L'analyse des données
# L'intégration avec d'autres services
