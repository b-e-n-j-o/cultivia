"""
Ce script génère des embeddings pour une liste d'événements en utilisant l'API OpenAI. Il prend en entrée un fichier JSON 
contenant des événements préparés, crée des embeddings via le modèle text-embedding-3-small, et sauvegarde les résultats 
dans trois fichiers distincts : un fichier NPZ pour les embeddings, un fichier JSON pour les métadonnées, et un fichier JSON 
pour les événements ayant échoué. Le script gère automatiquement les limites de taux d'API et inclut un système de réessai 
en cas d'échec.

Étapes du processus :
1. Chargement des variables d'environnement et vérification de la clé API OpenAI
2. Initialisation du générateur d'embeddings avec la clé API
3. Lecture du fichier JSON contenant les événements préparés
4. Pour chaque événement :
   - Extraction du texte à transformer en embedding
   - Appel à l'API OpenAI avec gestion des erreurs et des limites de taux
   - Stockage de l'embedding et des métadonnées associées
5. Sauvegarde des résultats :
   - Embeddings au format NPZ (numpy compressé)
   - Métadonnées au format JSON
   - Liste des événements échoués au format JSON
"""

import pandas as pd
import json
import time
import numpy as np
from openai import OpenAI, RateLimitError
from tqdm import tqdm
from typing import List, Dict, Tuple, Optional
import os
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

TODAY = datetime.now().strftime("%Y-%m-%d")

class EventEmbeddingsGenerator:
    def __init__(self, openai_api_key: str):
        if not openai_api_key:
            raise ValueError("🔑 API key OpenAI manquante")
        self.client = OpenAI(api_key=openai_api_key)
        self.retry_delay = 1
        
    def create_embedding(self, text: str, max_retries: int = 3) -> Optional[List[float]]:
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    input=text.strip(),
                    model="text-embedding-3-small"
                )
                self.retry_delay = 1
                return response.data[0].embedding
                
            except RateLimitError:
                wait_time = self.retry_delay * (2 ** attempt)
                print(f"⏳ Limite de taux atteinte, attente de {wait_time}s...")
                time.sleep(wait_time)
                self.retry_delay = wait_time
                
            except Exception as e:
                print(f"❌ Erreur embedding (tentative {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(self.retry_delay)
        
        return None

    def generate_events_embeddings(self, prepared_events: List[Dict]) -> Tuple[pd.DataFrame, List[Dict]]:
        embeddings = []
        failed_events = []
        
        progress_bar = tqdm(prepared_events, desc="🔄 Génération embeddings", 
                          unit="evt", ncols=100, disable=not os.isatty(0))
        
        for event in progress_bar:
            try:
                event_id = event.get('uuid', 'unknown')
                progress_bar.set_description(f"🔄 Traitement: {event_id[:8]}")
                
                if not event.get('embedding_text'):
                    raise ValueError("Texte d'embedding manquant")
                
                embedding = self.create_embedding(event['embedding_text'])
                if embedding is None:
                    raise Exception("Échec de création de l'embedding")
                
                # Copier toutes les métadonnées de l'événement et ajouter l'embedding
                event_data = event.copy()
                event_data['embedding'] = embedding
                event_data['id'] = len(embeddings)  # Ajouter un ID séquentiel
                embeddings.append(event_data)
                
                progress_bar.set_postfix({
                    "✅": len(embeddings),
                    "❌": len(failed_events)
                })
                
            except Exception as e:
                failed_event = {
                    'uuid': event_id,
                    'error': str(e),
                    'embedding_text': event.get('embedding_text', '')[:100]
                }
                failed_events.append(failed_event)
                print(f"\n❌ Échec pour {event_id}: {str(e)}")
        
        df = pd.DataFrame(embeddings)
        return df, failed_events

    def save_results(self, df: pd.DataFrame, failed_events: List[Dict], save_path: str):
        print("\n💾 Sauvegarde des résultats...")
        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)
        
        with tqdm(total=3, desc="📁 Sauvegarde", disable=not os.isatty(0)) as pbar:
            embeddings_array = np.array(df['embedding'].tolist())
            np.savez_compressed(
                save_path / f'embeddings_{TODAY}.npz',
                embeddings=embeddings_array
            )
            pbar.update(1)
            
            metadata = df.drop('embedding', axis=1).to_dict('records')
            with open(save_path / f'metadata_{TODAY}.json', 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            pbar.update(1)
            
            if failed_events:
                with open(save_path / f'failed_{TODAY}.json', 'w', encoding='utf-8') as f:
                    json.dump(failed_events, f, ensure_ascii=False, indent=2)
            pbar.update(1)

def run_events_pipeline(prepared_events_path: str, openai_api_key: str, save_path: str) -> Optional[pd.DataFrame]:
    print("🚀 Démarrage du pipeline")
    
    try:
        if not os.path.exists(prepared_events_path):
            raise FileNotFoundError(f"Fichier non trouvé: {prepared_events_path}")
            
        with open(prepared_events_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        prepared_events = data.get('events', [])
        if not prepared_events:
            raise ValueError("Aucun événement trouvé dans le fichier")
            
        print(f"✅ {len(prepared_events)} événements chargés")
        
        generator = EventEmbeddingsGenerator(openai_api_key)
        df, failed_events = generator.generate_events_embeddings(prepared_events)
        
        success_rate = (len(df)/len(prepared_events))*100
        print(f"\n📊 Résultats:")
        print(f"📌 Total: {len(prepared_events)}")
        print(f"✅ Réussis: {len(df)} ({success_rate:.1f}%)")
        print(f"❌ Échoués: {len(failed_events)}")
        
        if len(df) > 0:
            generator.save_results(df, failed_events, save_path)
            return df
        else:
            print("⚠️ Aucun embedding généré")
            return None
            
    except Exception as e:
        print(f"❌ Erreur pipeline: {str(e)}")
        return None

if __name__ == "__main__":
    load_dotenv()
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("API key manquante dans .env")
        
    PREPARED_EVENTS_PATH = f"../data/json_prepared/{TODAY}.json"
    SAVE_PATH = f"../data/embeddings/{TODAY}"
    
    df = run_events_pipeline(PREPARED_EVENTS_PATH, OPENAI_API_KEY, SAVE_PATH)