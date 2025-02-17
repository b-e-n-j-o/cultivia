"""
Script de Parsage d'Événements Culturels (HTML vers JSON)
--------------------------------------------------------

Ce script est conçu pour extraire et structurer les informations d'événements culturels
à partir de pages HTML. Il transforme des pages web d'événements en données JSON structurées
et organisées.

Fonctionnalités principales :
- Extraction automatisée des informations clés des événements (titre, date, lieu, prix, etc.)
- Traitement par lot de multiples fichiers HTML
- Organisation chronologique des données (par date)
- Système de logging détaillé pour le suivi des opérations
- Gestion robuste des erreurs

Structure des données extraites :
- Informations générales (titre, date, heure)
- Localisation (lieu, adresse)
- Détails pratiques (prix, billetterie)
- Contenu (description, discipline)
- Métadonnées (organisateur, type de participation)
- Médias (images, liens)

Utilisation :
1. Placer les fichiers HTML dans le dossier 'data/html_files/[date]/'
2. Exécuter le script
3. Récupérer les données JSON dans 'data/json_files/[date].json'

Le script est conçu pour être robuste et maintenant, avec une gestion complète des erreurs
et un système de logging détaillé pour faciliter le débogage et le suivi des opérations.

"""

from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
import urllib.parse
import logging
from typing import List, Dict, Optional
import os
from pathlib import Path

class EventParser:
    def __init__(self, html_content):
        self.setup_logging()
        self.soup = BeautifulSoup(html_content, 'html.parser')
        
    def setup_logging(self):
        custom_format = logging.Formatter(
            '%(asctime)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # Suppression des handlers existants
        logger.handlers = []
        
        # Handler pour la console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(custom_format)
        logger.addHandler(console_handler)
        
        # Handler pour le fichier
        file_handler = logging.FileHandler('parsing.log')
        file_handler.setFormatter(custom_format)
        logger.addHandler(file_handler)
        
    def extract_discipline_label(self, encoded_string: str) -> Optional[str]:
        try:
            logging.info("🏷️  Décodage des tags de discipline")
            decoded = urllib.parse.unquote(encoded_string)
            data = json.loads(decoded)
            
            if isinstance(data, list) and len(data) > 0:
                discipline = data[0].get('labelFr')
                logging.info(f"✅ Discipline trouvée: {discipline}")
                return discipline
            
            logging.warning("⚠️  Aucune discipline trouvée dans les données")
            return None
                
        except json.JSONDecodeError as e:
            logging.error(f"❌ Erreur décodage JSON des disciplines: {e}")
            return None
        except Exception as e:
            logging.error(f"❌ Erreur inattendue extraction discipline: {e}")
            return None
        
    def extract_event_info(self):
        logging.info("🔍 Début extraction des informations de l'événement")
        try:
            event_data = {
                "titre": self._get_title(),
                "date": self._get_date(),
                "heure": self._get_time(),
                "lieu": self._get_location(),
                "prix": self._get_price(),
                "description": self._get_description(),
                "organisateur": self._get_organizer(),
                "image_url": self._get_image_url(),
                "site_web": self._get_website(),
                "billetterie_url": self._get_ticket_url(),
                "discipline": self._get_discipline(),
                "type_participation": self._get_participation_type(),
                "meta_data": self._get_meta_data()
            }
            
            # Log des informations extraites
            for key, value in event_data.items():
                if value:
                    if isinstance(value, (dict, list)):
                        logging.info(f"📝 {key}: {len(value)} éléments extraits")
                    else:
                        preview = str(value)[:50] + '...' if len(str(value)) > 50 else str(value)
                        logging.info(f"📝 {key}: {preview}")
            
            return event_data
            
        except Exception as e:
            logging.error(f"❌ Erreur extraction données: {e}")
            return None
    
    def _get_discipline(self) -> Optional[str]:
        logging.info("🎭 Extraction de la discipline")
        try:
            lvc_tags = self.soup.find('lvc-tags', class_='webcomponent_lvc-tags')
            if not lvc_tags:
                logging.warning("⚠️  Élément lvc-tags non trouvé")
                return None
                
            discipline_tags = lvc_tags.get('data-discipline-tags')
            if not discipline_tags:
                logging.warning("⚠️  Tags de discipline non trouvés")
                return None

            return self.extract_discipline_label(discipline_tags)

        except Exception as e:
            logging.error(f"❌ Erreur extraction discipline: {e}")
            return None
    
    def _get_title(self):
        title = self.soup.find('h1')
        return title.text.strip() if title else None
    
    def _get_date(self):
        date_elem = self.soup.find('div', {'id': 'eventDate'})
        return date_elem.text.strip() if date_elem else None
    
    def _get_time(self):
        time_elem = self.soup.find('div', {'id': 'eventTime'})
        return time_elem.text.strip() if time_elem else None
    
    def _get_location(self):
        location = {}
        place_elem = self.soup.find('a', {'id': 'eventPlace'})
        location_elem = self.soup.find('div', {'id': 'eventLocation'})
        
        if place_elem:
            location['nom'] = place_elem.text.strip()
            location['url'] = place_elem['href'] if 'href' in place_elem.attrs else None
        
        if location_elem:
            location['adresse'] = location_elem.text.strip()
            
        return location
    
    def _get_price(self):
        price_elem = self.soup.find('div', {'id': 'ticketText'})
        return price_elem.text.strip() if price_elem else None
    
    def _get_description(self):
        try:
            description_parts = []
            
            first_sentence = self.soup.find('div', {'id': 'about-first-sentence'})
            if first_sentence:
                description_parts.append(first_sentence.text.strip())
            
            full_description = self.soup.find('div', {'id': 'about-description'})
            if full_description:
                description_parts.append(full_description.text.strip())
            
            if description_parts:
                return ' '.join(description_parts)
            
            return None
            
        except Exception as e:
            logging.error(f"❌ Erreur extraction description: {e}")
            return None
    
    def _get_organizer(self):
        organizer = {}
        artist_elem = self.soup.find('a', {'id': 'eventArtist'})
        if artist_elem:
            organizer['nom'] = artist_elem.text.strip()
            organizer['url'] = artist_elem['href'] if 'href' in artist_elem.attrs else None
        return organizer
    
    def _get_image_url(self):
        og_image = self.soup.find('meta', property='og:image')
        if og_image:
            return og_image['content']
        
        img_elem = self.soup.find('img', {'class': 'lvc-image_image'})
        return img_elem['src'] if img_elem else None
    
    def _get_website(self):
        website_link = self.soup.find('a', {'class': 'lvc-button-medium is-transparent'})
        return website_link['href'] if website_link else None
    
    def _get_participation_type(self):
        participation_elem = self.soup.find('div', text=re.compile('En présentiel|Virtuel'))
        return participation_elem.text.strip() if participation_elem else None
    
    def _get_meta_data(self):
        script_tag = self.soup.find('script', type='application/ld+json')
        if script_tag:
            try:
                return json.loads(script_tag.string)
            except json.JSONDecodeError:
                return None
        return None
        
    def _get_ticket_url(self) -> Optional[str]:
        logging.info("🎟️  Recherche URL de billetterie")
        try:
            ticket_elem = self.soup.find('lvc-event-ticket', {'slot': 'ticket'})
            if ticket_elem and 'href' in ticket_elem.attrs:
                logging.info("✅ URL de billetterie trouvée (méthode 1)")
                return ticket_elem['href']

            ticket_elem = self.soup.select_one('lvc-event-ticket a[href]')
            if ticket_elem:
                logging.info("✅ URL de billetterie trouvée (méthode 2)")
                return ticket_elem['href']

            all_links = self.soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                if any(domain in href.lower() for domain in ['billet', 'ticket', 'zeffy', 'lepointdevente']):
                    logging.info("✅ URL de billetterie trouvée (méthode 3)")
                    return href

            logging.warning("⚠️  Aucune URL de billetterie trouvée")
            return None

        except Exception as e:
            logging.error(f"❌ Erreur recherche URL billetterie: {e}")
            return None

def save_event_info(html_content, output_file):
    logging.info(f"🎯 Traitement d'un nouvel événement")
    parser = EventParser(html_content)
    event_data = parser.extract_event_info()
    
    if event_data:
        try:
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    all_events = json.load(f)
                    logging.info(f"📚 {len(all_events)} événements déjà dans le fichier")
            except (FileNotFoundError, json.JSONDecodeError):
                logging.info("📝 Création d'un nouveau fichier d'événements")
                all_events = []
            
            all_events.append(event_data)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_events, f, ensure_ascii=False, indent=2)
            logging.info(f"💾 Événement sauvegardé dans {output_file}")
            logging.info(f"📊 Total événements: {len(all_events)}")
            
        except Exception as e:
            logging.error(f"❌ Erreur sauvegarde données: {e}")
    else:
        logging.error("❌ Échec extraction données de l'événement")

if __name__ == "__main__":
    logging.info("🚀 Démarrage du parser d'événements")
    
    os.makedirs('../data/json_files', exist_ok=True)
    logging.info("📁 Dossier de sortie vérifié")
    
    today = datetime.now().strftime('%Y-%m-%d')
    output_file = f'../data/json_files/{today}.json'
    logging.info(f"📄 Fichier de sortie: {output_file}")
    
    html_dir = f'../data/html_files/{today}'
    html_files = [f for f in os.listdir(html_dir) if f.endswith('.html')]
    logging.info(f"🔍 {len(html_files)} fichiers HTML trouvés")
    
    for i, filename in enumerate(html_files, 1):
        input_path = os.path.join(html_dir, filename)
        logging.info(f"📖 Traitement fichier {i}/{len(html_files)}: {filename}")
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            save_event_info(html_content, output_file)
            
        except Exception as e:
            logging.error(f"❌ Erreur lecture fichier {filename}: {e}")
            
    logging.info("🏁 Traitement terminé")