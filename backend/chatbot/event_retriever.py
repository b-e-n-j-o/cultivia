from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
import time  # Un seul import de time ici
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv
import os
from date_extractor import EnhancedDateExtractorChain
from query_rephraser import QueryRephraser
import pytz

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventIDRetriever:
    def __init__(self, openai_api_key: str, pinecone_api_key: str, index_name: str):
        """Initialise le retrieveur avec les clés API nécessaires"""
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index = self.pc.Index(index_name)
        self.date_extractor = EnhancedDateExtractorChain(openai_api_key)
        self.query_rephraser = QueryRephraser()  # Ajout du rephraser

    def build_discipline_filter(self, disciplines: List[str]) -> Dict:
        """
        Construit un filtre Pinecone pour les disciplines.
        """
        if not disciplines:
            return {}
            
        return {
            "discipline": {
                "$in": disciplines
            }
        }

    def merge_filters(self, date_filter: Dict, discipline_filter: Dict) -> Dict:
        """
        Combine les filtres de date et de discipline pour Pinecone.
        """
        if not date_filter and not discipline_filter:
            return {}
        if not date_filter:
            return discipline_filter
        if not discipline_filter:
            return date_filter
            
        # Combine les deux filtres avec un $and
        return {
            "$and": [
                date_filter,
                discipline_filter
            ]
        }

    def group_similar_events(self, events: List[Dict]) -> List[Dict]:
        """
        Regroupe les événements similaires et limite aux 10 meilleurs résultats
        Utilisé pour l'affichage sur le site web
        """
        try:
            from collections import defaultdict
            event_groups = defaultdict(list)
            
            # Regroupement des événements par titre
            for event in events:
                title = event['title'].strip()
                event_groups[title].append(event)
        
            grouped_events = []
            
            for title, similar_events in event_groups.items():
                grouped_event = {
                    'title': title,
                    'date': [],
                    'time': [],
                    'description': similar_events[0].get('description', ''),
                    'venue': similar_events[0].get('venue', ''),
                    'city': similar_events[0].get('city', ''),
                    'discipline': similar_events[0].get('discipline', ''),
                    'price': similar_events[0].get('price', ''),
                    'url': similar_events[0].get('url', ''),
                    'image_url': similar_events[0].get('image_url', ''),
                    'event_id': similar_events[0].get('event_id', ''),
                    'score': max(event.get('score', 0) for event in similar_events),
                    'date_unix': similar_events[0].get('date_unix', '')
                }
                
                # Collecter dates uniques
                seen_dates = set()
                for event in similar_events:
                    date_time = (event.get('date', ''), event.get('time', ''))
                    if date_time not in seen_dates and date_time[0] and date_time[1]:
                        grouped_event['date'].append(date_time[0])
                        grouped_event['time'].append(date_time[1])
                        seen_dates.add(date_time)
            
                if grouped_event['date']:
                    dates_times = sorted(zip(grouped_event['date'], grouped_event['time']), 
                                      key=lambda x: x[0])
                    sorted_dates, sorted_times = zip(*dates_times)
                    grouped_event['date'] = list(sorted_dates)
                    grouped_event['time'] = list(sorted_times)
                    grouped_events.append(grouped_event)
        
            # Tri par score et limitation aux 10 meilleurs résultats
            return sorted(grouped_events, key=lambda x: x['score'], reverse=True)[:10]
                
        except Exception as e:
            logger.error(f"Erreur lors du regroupement des événements: {str(e)}")
            return events[:10]  # Limite aussi en cas d'erreur

    def get_top_events_for_prompt(self, grouped_events: List[Dict], max_events: int = 5) -> List[Dict]:
        """
        Sélectionne les meilleurs événements pour le prompt LLM
        """
        return grouped_events[:max_events]

    def extract_date_filter(self, query: str) -> Tuple[Dict, Optional[str]]:
        """
        Extrait la date et construit le filtre pour Pinecone en utilisant une plage de 24h
        en respectant le fuseau horaire de Montréal
        """
        try:
            # Définir le fuseau horaire de Montréal
            montreal_tz = pytz.timezone('America/Montreal')
            
            date_info = self.date_extractor.extract_date(query)
            logger.info(f"Résultat extraction date: {date_info}")
            
            if not (hasattr(date_info, 'date_found') and date_info.date_found):
                return {}, None

            filter_dict = {}
            target_date = None

            if date_info.is_interval and hasattr(date_info, 'interval_bounds'):
                # Pour les intervalles
                start_naive = datetime.fromisoformat(date_info.interval_bounds['start'])
                end_naive = datetime.fromisoformat(date_info.interval_bounds['end'])
                
                # Localiser les dates dans le fuseau horaire de Montréal
                start_date = montreal_tz.localize(start_naive.replace(hour=0, minute=0, second=0))
                end_date = montreal_tz.localize(end_naive.replace(hour=23, minute=59, second=59))
                
                filter_dict["date_unix"] = {
                    "$gte": int(start_date.timestamp()),
                    "$lte": int(end_date.timestamp())
                }
                target_date = date_info.interval_bounds['start']
                
            elif hasattr(date_info, 'dates') and date_info.dates:
                # Pour une date spécifique
                date_str = date_info.dates[0]
                date_naive = datetime.fromisoformat(date_str)
                
                # Début de la journée à Montréal (00:00:00)
                start_date = montreal_tz.localize(
                    date_naive.replace(hour=0, minute=0, second=0)
                )
                
                # Fin de la journée à Montréal (23:59:59)
                end_date = montreal_tz.localize(
                    date_naive.replace(hour=23, minute=59, second=59)
                )
                
                filter_dict["date_unix"] = {
                    "$gte": int(start_date.timestamp()),
                    "$lte": int(end_date.timestamp())
                }
                target_date = date_str

            logger.info(f"Filtre de date construit: {filter_dict}")
            logger.info(f"Timestamps en format lisible:")
            logger.info(f"Début: {datetime.fromtimestamp(filter_dict['date_unix']['$gte'], montreal_tz)}")
            logger.info(f"Fin: {datetime.fromtimestamp(filter_dict['date_unix']['$lte'], montreal_tz)}")
            
            return filter_dict, target_date

        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de la date: {str(e)}")
            return {}, None

    def search(self, query: str, top_k: int = 10) -> Tuple[List[Dict], List[Dict], Optional[str]]:
        try:
            # 1. Reformulation et analyse de la requête
            query_analysis = self.query_rephraser.analyze_query(query)
            logger.info(f"Requête originale: {query}")
            logger.info(f"Reformulations: {query_analysis.reformulations}")
            logger.info(f"Disciplines identifiées: {query_analysis.disciplines}")

            # 2. Extraction de la date
            date_filter, target_date = self.extract_date_filter(query)
            
            # 3. Construction du filtre de disciplines
            discipline_filter = self.build_discipline_filter(query_analysis.disciplines)
            
            # 4. Fusion des filtres
            combined_filter = self.merge_filters(date_filter, discipline_filter)
            logger.info(f"Filtre combiné: {combined_filter}")

            # 5. Création des embeddings pour chaque reformulation
            all_results = []
            for reformulation in [query] + query_analysis.reformulations:
                embedding = self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=reformulation
                ).data[0].embedding
                
                # Requête Pinecone avec le filtre combiné
                results = self.index.query(
                    vector=embedding,
                    filter=combined_filter,
                    top_k=top_k,
                    include_metadata=True
                )
                
                # Ajout des résultats avec leur score
                all_results.extend([
                    {
                        'event_id': match.id,
                        'score': match.score,
                        'title': match.metadata.get('title', 'Titre non disponible'),
                        'description': match.metadata.get('description', ''),
                        'venue': match.metadata.get('venue', ''),
                        'city': match.metadata.get('city', ''),
                        'date': match.metadata.get('date', ''),
                        'time': match.metadata.get('time', ''),
                        'discipline': match.metadata.get('discipline', ''),
                        'price': match.metadata.get('price', ''),
                        'url': match.metadata.get('event_url', ''),
                        'image_url': match.metadata.get('image_url', ''),
                        'date_unix': match.metadata.get('date_unix', '')
                    }
                    for match in results.matches
                ])

            # 6. Dédoublonnage et tri des résultats par score
            unique_results = self.deduplicate_results(all_results)
            all_grouped_events = self.group_similar_events(unique_results)
            top_events_for_prompt = self.get_top_events_for_prompt(all_grouped_events)

            return all_grouped_events, top_events_for_prompt, target_date

        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {str(e)}", exc_info=True)
            return [], [], None

    def deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """
        Dédoublonne les résultats en gardant le meilleur score pour chaque événement.
        """
        seen_events = {}
        for result in results:
            event_id = result['event_id']
            if event_id not in seen_events or result['score'] > seen_events[event_id]['score']:
                seen_events[event_id] = result
        
        return list(seen_events.values())

def main():
    import time as timing  # Import local avec un alias différent
    start_exec_time = timing.time()  # Utilisation de l'alias
    
    # Chargement des variables d'environnement
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    INDEX_NAME = "lavitrine"
    
    if not all([PINECONE_API_KEY, OPENAI_API_KEY]):
        logger.error("Clés API manquantes dans les variables d'environnement")
        return
        
    try:
        # Initialisation du retrieveur
        retriever = EventIDRetriever(
            openai_api_key=OPENAI_API_KEY,
            pinecone_api_key=PINECONE_API_KEY,
            index_name=INDEX_NAME
        )
        
        # Demande de la requête à l'utilisateur
        query = input("Entrez votre recherche d'événement : ")
        
        # Recherche
        all_events, top_events, target_date = retriever.search(query)
        
        # Calcul du temps d'exécution
        execution_time = timing.time() - start_exec_time
        
        # Affichage des résultats détaillés
        print(f"\nRésultats pour la requête: '{query}'")
        print(f"Temps d'exécution: {execution_time:.2f} secondes")
        if target_date:
            print(f"Date ciblée: {target_date}")
            
        for result in all_events:
            print(f"\nID: {result['event_id']}")
            print(f"Titre: {result['title']}")
            print(f"Score: {result['score']:.4f}")
            print(f"Date Unix: {result['date_unix']}")
            print(f"Lieu: {result['venue']} à {result['city']}")
            
            # Affichage des dates
            if isinstance(result['date'], list):
                print("Dates disponibles:")
                for date, time in zip(result['date'], result['time']):
                    print(f"- Le {date} à {time}")
            else:
                print(f"Date: {result['date']} à {result['time']}")
                
            print(f"Discipline(s): {', '.join(result['discipline'])}")
            print(f"Prix: {result['price']}")
            print(f"URL: {result['url']}")
            print("-" * 50)
            
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution: {str(e)}")

if __name__ == "__main__":
    main()