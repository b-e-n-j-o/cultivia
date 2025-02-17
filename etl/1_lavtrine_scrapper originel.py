"""
Script de scraping pour le site LaVitrine.com

Ce script permet d'extraire automatiquement les liens des événements culturels 
du site LaVitrine.com. Il utilise Playwright pour l'automatisation du navigateur 
et implémente les fonctionnalités suivantes :

1. URLManager :
   - Gère le stockage et le suivi des URLs déjà visitées
   - Utilise un système de hachage pour éviter les doublons et ainsi ne recupérer que les nouvelles URLs
   - Sauvegarde les nouvelles URLs dans des fichiers JSON datés

La gestion des doublons dans ce script repose sur un système de hachage efficace. 
Chaque URL est convertie en une empreinte numérique unique (hash) via l'algorithme 
SHA-256. Ces hashes sont stockés dans un ensemble (set) et sauvegardés dans un 
fichier JSON, permettant une vérification rapide et persistante des URLs déjà 
visitées. Lorsqu'une nouvelle URL est découverte, son hash est calculé et 
comparé à l'ensemble existant : si le hash n'existe pas, l'URL est considérée 
comme nouvelle et ajoutée à la collection.

La recherche dans un ensemble (set) de hashes offre un gain de performance 
significatif avec une complexité algorithmique de O(1) - temps constant - comparé à 
une recherche directe dans une liste d'URLs qui serait en O(n).

2. LaVitrineSpider :
   - Configure la connexion via un proxy
   - Navigue à travers les pages de résultats de recherche
   - Extrait les liens des événements de manière asynchrone
   - Implémente des délais et des vérifications pour assurer une extraction fiable
   - S'arrête automatiquement après deux pages vides consécutives ou 100 pages

Le script utilise asyncio pour les opérations asynchrones et inclut des 
mécanismes de gestion d'erreurs et de logging pour suivre le processus 
d'extraction.
"""

import asyncio
from playwright.async_api import async_playwright
import json
import time
from datetime import datetime
import os
import urllib.parse
import hashlib
from typing import Set, List
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

class URLManager:
    def __init__(self):
        self.base_dir = 'data/event_links'
        self.nouveaux_liens_dir = os.path.join(self.base_dir, 'nouveaux_liens')
        self.hash_file = os.path.join(self.base_dir, 'urls_hash.json')
        self.known_hashes = self._load_known_hashes()

    def _load_known_hashes(self) -> Set[str]:
        """Charge les hashes connus depuis le fichier JSON."""
        if os.path.exists(self.hash_file):
            with open(self.hash_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()

    def _save_known_hashes(self):
        """Sauvegarde les hashes connus dans le fichier JSON."""
        os.makedirs(os.path.dirname(self.hash_file), exist_ok=True)
        with open(self.hash_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.known_hashes), f, indent=2)

    def _hash_url(self, url: str) -> str:
        """Génère un hash unique pour une URL."""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    def filter_new_urls(self, urls: List[str]) -> List[str]:
        """Filtre les nouvelles URLs qui n'ont pas encore été vues."""
        new_urls = []
        for url in urls:
            url_hash = self._hash_url(url)
            if url_hash not in self.known_hashes:
                new_urls.append(url)
                self.known_hashes.add(url_hash)
        return new_urls

    def save_new_urls(self, urls: List[str]):
        """Sauvegarde les nouvelles URLs dans un fichier daté."""
        if not urls:
            return

        # Créer le répertoire des nouveaux liens
        os.makedirs(self.nouveaux_liens_dir, exist_ok=True)
        
        # Générer le nom du fichier avec la date
        timestamp = datetime.now().strftime('%Y_%m_%d')
        filename = os.path.join(self.nouveaux_liens_dir, f'{timestamp}.json')
        
        # Sauvegarder les nouvelles URLs
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(urls, f, indent=2, ensure_ascii=False)
        
        # Mettre à jour le fichier de hashes
        self._save_known_hashes()
        
        print(f"Nouvelles URLs sauvegardées dans {filename}")
        print(f"Nombre de nouvelles URLs : {len(urls)}")

class LaVitrineSpider:
    def __init__(self):
        self.base_url = os.getenv('TARGET_SITE_URL')
        self.base_query = {
            "facets": [{"name": "hasPublishedEvents", "options": [{"value": "true", "selected": True, "available": True}]}],
            "query": "",
            "page": 0,
            "modal": "events_search",
            "sorting": "",
            "dateFilters": [],
            "dateAnalyticsValue": "",
            "locationLabel": os.getenv('LOCATION_LABEL'),
            "options": {
                "hitsPerPage": {"default": 300, "events_search": 300, "exhibitions_search": 0, "eventseries_search": 0, "places_full": 0, "artists": 0},
                "aroundRadius": {"default": 30000, "events_search": 30000, "exhibitions_search": 30000, "eventseries_search": 30000, "places_full": 30000, "artists": None},
                "aroundLatLng": {
                    "events_search": f"{os.getenv('LOCATION_LAT')},{os.getenv('LOCATION_LNG')}",
                    "exhibitions_search": f"{os.getenv('LOCATION_LAT')},{os.getenv('LOCATION_LNG')}",
                    "eventseries_search": f"{os.getenv('LOCATION_LAT')},{os.getenv('LOCATION_LNG')}",
                    "places_full": f"{os.getenv('LOCATION_LAT')},{os.getenv('LOCATION_LNG')}",
                    "artists": None
                },
                "page": {"default": 0, "events_search": 0, "exhibitions_search": 0, "eventseries_search": 0, "places_full": 0, "artists": 0},
                "paginationLimitedTo": {"events_search": None, "exhibitions_search": None, "eventseries_search": None, "places_full": None, "artists": None},
                "numericFilters": []
            }
        }
        
        self.proxy = {
            'server': f"http://{os.getenv('PROXY_SERVER')}",
            'username': os.getenv('PROXY_USERNAME'),
            'password': os.getenv('PROXY_PASSWORD')
        }
        self.url_manager = URLManager()

    def get_url_for_page(self, page_number):
        # Copier la requête de base
        query = self.base_query.copy()
        # Mettre à jour le numéro de page
        query["options"]["page"]["events_search"] = page_number
        # Encoder l'URL
        encoded_query = urllib.parse.quote(json.dumps(query))
        url = f"{self.base_url}/fr/recherche?query={encoded_query}"
        return url

    async def get_event_links_from_page(self, page, page_number):
        url = self.get_url_for_page(page_number)
        try:
            print(f"\n{'='*50}")
            print(f"Chargement de la page {page_number}...")
            print(f"URL: {url}")
            print(f"{'='*50}\n")
            
            await page.goto(url)
            
            # Attendre 10 secondes pour s'assurer que la page est bien chargée
            print("Attente de 10 secondes pour le chargement complet...")
            await asyncio.sleep(10)
            
            # Attendre que la page charge complètement
            await page.wait_for_load_state('networkidle')
            
            print("Recherche des liens d'événements...")
            # Attendre que les éléments des événements soient présents
            await page.wait_for_selector("a[href*='/evenement/']", state="visible")
            
            # Extraire les liens
            event_links = await page.eval_on_selector_all(
                "a[href*='/evenement/']",
                "elements => elements.map(el => el.href)"
            )
            
            # Dédupliquer les liens
            unique_links = list(set(event_links))
            print(f"Nombre de liens uniques trouvés sur la page {page_number}: {len(unique_links)}")
            
            return unique_links

        except Exception as e:
            print(f"Erreur lors du scraping de la page {page_number}: {e}")
            return []

    async def get_all_event_links(self):
        async with async_playwright() as p:
            print("Lancement du navigateur...")
            browser = await p.chromium.launch(
                headless=True,
                proxy={
                    'server': self.proxy['server'],
                    'username': self.proxy['username'],
                    'password': self.proxy['password']
                }
            )
            
            try:
                context = await browser.new_context()
                page = await context.new_page()
                
                all_links = set()
                page_number = 0
                consecutive_empty_pages = 0
                
                while True:
                    links = await self.get_event_links_from_page(page, page_number)
                    
                    if not links:
                        consecutive_empty_pages += 1
                        print(f"Page vide trouvée ({consecutive_empty_pages} pages vides consécutives)")
                        if consecutive_empty_pages >= 2:
                            print("Deux pages vides consécutives trouvées. Arrêt du scraping.")
                            break
                    else:
                        consecutive_empty_pages = 0
                        all_links.update(links)
                        print(f"Total de liens uniques collectés jusqu'à présent: {len(all_links)}")
                    
                    # Pause entre les pages
                    page_number += 1
                    if page_number < 100:  # Limite de sécurité
                        print("\nPause de 2 secondes avant la prochaine page...")
                        await asyncio.sleep(2)
                    else:
                        print("Limite de 100 pages atteinte. Arrêt du scraping.")
                        break
                
                return list(all_links)

            except Exception as e:
                print(f"Erreur lors du scraping: {e}")
                return []
            
            finally:
                await browser.close()

    def save_links_to_file(self, links):
        try:
            # Filtrer pour ne garder que les nouvelles URLs
            new_links = self.url_manager.filter_new_urls(links)
            
            # Sauvegarder les nouvelles URLs
            self.url_manager.save_new_urls(new_links)
            
            print(f"Nombre total d'URLs traitées : {len(links)}")
            print(f"Nombre de nouvelles URLs : {len(new_links)}")
            
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des liens: {e}")

async def main():
    spider = LaVitrineSpider()
    print("Démarrage du spider...")
    
    # Obtenir tous les liens de toutes les pages
    event_links = await spider.get_all_event_links()
    
    print(f"\nNombre total de liens trouvés: {len(event_links)}")
    if event_links:
        print("\nExemples de liens:")
        for link in event_links[:5]:
            print(link)
        
        # Sauvegarder tous les liens dans un fichier
        spider.save_links_to_file(event_links)

if __name__ == "__main__":
    asyncio.run(main())