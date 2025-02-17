import requests
import json
import os
from urllib.parse import urlparse
import time
from pathlib import Path
import logging
from datetime import datetime
import urllib3
import random
from tqdm import tqdm
# // Seulement les 10 premiers liens et sans IP rotation

# Désactiver les avertissements HTTPS
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class HTMLScraper:
    def __init__(self):
        self.session = requests.Session()
        self.setup_logging()
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        
    def setup_logging(self):
        # Format personnalisé pour les logs
        custom_format = logging.Formatter(
            '%(asctime)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Configuration du logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # Handler pour la console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(custom_format)
        
        # Handler pour le fichier
        file_handler = logging.FileHandler('scraping.log')
        file_handler.setFormatter(custom_format)
        
        # Suppression des handlers existants
        logger.handlers = []
        
        # Ajout des nouveaux handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    def load_latest_urls(self):
        """Charge les URLs depuis le fichier le plus récent dans nouveaux_liens"""
        try:
            nouveaux_liens_dir = 'data/event_links/nouveaux_liens'
            files = os.listdir(nouveaux_liens_dir)
            json_files = [f for f in files if f.endswith('.json')]
            
            if not json_files:
                logging.error("🚫 Aucun fichier de nouveaux liens trouvé")
                return []
                
            latest_file = max(json_files)
            file_path = os.path.join(nouveaux_liens_dir, latest_file)
            logging.info(f"📂 Chargement du fichier: {latest_file}")
            return self.load_urls(file_path)
            
        except Exception as e:
            logging.error(f"🚫 Erreur lors du chargement des nouveaux liens: {e}")
            return []

    def load_urls(self, json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and 'urls' in data:
                    return data['urls']
                else:
                    logging.error("🚫 Format JSON invalide")
                    return []
        except Exception as e:
            logging.error(f"🚫 Erreur de chargement du fichier JSON: {e}")
            return []

    def get_safe_filename(self, url):
        parsed = urlparse(url)
        filename = parsed.netloc + parsed.path
        filename = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in filename)
        return filename[:200] + '.html'

    def scrape_url(self, url):
        try:
            wait_time = random.uniform(3, 7)
            logging.info(f"⏳ Temps d'attente avant visite: {wait_time:.1f} secondes")
            time.sleep(wait_time)
            
            logging.info(f"🌐 Visite de la page: {url}")
            logging.info(f"🔍 Navigateur utilisé: {self.user_agent}")
            start_time = time.time()
            
            headers = {
                'User-Agent': self.user_agent
            }
            
            response = self.session.get(
                url,
                headers=headers,
                timeout=60
            )
            
            response.raise_for_status()
            
            elapsed_time = time.time() - start_time
            logging.info(f"⚡ Page chargée en {elapsed_time:.2f} secondes")
            
            return response.text

        except requests.exceptions.RequestException as e:
            logging.error(f"⚠️ Erreur de requête: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"❌ Erreur inattendue: {str(e)}")
            return None

    def save_html(self, html_content, filename):
        if not html_content:
            return False
            
        today = datetime.now().strftime('%Y-%m-%d')
        output_dir = Path(f'../data/html_files/{today}')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = output_dir / filename
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logging.info(f"💾 Contenu sauvegardé: {file_path}")
            return True
        except Exception as e:
            logging.error(f"📝 Erreur de sauvegarde: {e}")
            return False

    def process_urls(self, delay=2):
        urls = self.load_latest_urls()
        if not urls:
            logging.error("📭 Aucune URL à traiter")
            return

        total_urls = len(urls)
        logging.info(f"🎯 Début du traitement de {total_urls} URLs")

        for i, url in enumerate(urls, 1):
            logging.info(f"📍 Progression: {i}/{total_urls}")
            
            html_content = self.scrape_url(url)
            if html_content:
                filename = self.get_safe_filename(url)
                self.save_html(html_content, filename)
            
            if i < len(urls):
                wait_time = random.uniform(delay * 0.8, delay * 1.2)
                logging.info(f"⏳ Pause de {wait_time:.1f} secondes avant la prochaine URL")
                time.sleep(wait_time)

def main():
    logging.info("🚀 Démarrage du scraper")
    scraper = HTMLScraper()
    
    urls = scraper.load_latest_urls()
    if urls:
        # Limite à 10 URLs
        urls = urls[:10]
        total_urls = len(urls)
        logging.info(f"📚 Traitement des {total_urls} premières URLs")
        
        with tqdm(total=total_urls, desc="Progression", unit="URL") as pbar:
            for i, url in enumerate(urls, 1):
                logging.info(f"🔄 Traitement URL {i}/{total_urls}")
                html_content = scraper.scrape_url(url)
                if html_content:
                    filename = scraper.get_safe_filename(url)
                    scraper.save_html(html_content, filename)
                
                if i < total_urls:
                    wait_time = random.uniform(1.5, 4)
                    logging.info(f"⏳ Pause de {wait_time:.1f} secondes")
                    time.sleep(wait_time)
                
                pbar.update(1)
    else:
        logging.info("📭 Aucune URL à traiter")
    
    logging.info("🏁 Scraping terminé")

if __name__ == "__main__":
    main()