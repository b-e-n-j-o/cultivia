"""
Ce script permet d'indexer des événements culturels dans une base de données vectorielle Pinecone.
Il prend en entrée des embeddings (représentations vectorielles) et des métadonnées d'événements,
les formate et les charge par lots dans un index Pinecone pour permettre une recherche sémantique.

Étapes principales :
1. Initialisation de la connexion à Pinecone
2. Chargement des embeddings (fichier .npz) et métadonnées (fichier .json)
3. Formatage des métadonnées pour Pinecone (ajout des champs requis)
4. Indexation par lots avec gestion des erreurs et retries
5. Test de l'index avec une requête de vérification
6. Dans le main : test avec un sous-ensemble de 10 événements
"""

from pinecone import Pinecone
import numpy as np
import json
from tqdm import tqdm
import time
from typing import Dict, Any, List
from dotenv import load_dotenv
import os
from datetime import datetime
import backoff

TODAY = datetime.now().strftime("%Y-%m-%d")

class EventIndexer:
    def __init__(self, pinecone_api_key: str, index_name: str):
        if not pinecone_api_key:
            raise ValueError("🔑 Clé API Pinecone manquante")
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index = self.pc.Index(index_name)
        self.retry_delay = 1
            
    def format_metadata(self, metadata: Dict) -> Dict[str, Any]:
        """Formate les métadonnées pour Pinecone"""
        formatted = {
            'id': str(metadata.get('id', '')),
            'uuid': str(metadata.get('uuid', '')),
            'event_url': str(metadata.get('event_url', '')),
            'title': str(metadata.get('title', '')),
            'description': str(metadata.get('description', '')),
            'embedding_text': str(metadata.get('embedding_text', '')),
            'discipline': str(metadata.get('discipline', '')),
            'price': str(metadata.get('price', '')),
            'date': str(metadata.get('date', '')),
            'date_iso': str(metadata.get('date_iso', '')),
            'time': str(metadata.get('time', '')),
            'performer': str(metadata.get('performer', '')),
            'organizer': str(metadata.get('organizer', '')),
            'contributor': str(metadata.get('contributor', '')),
            'image_url': str(metadata.get('image_url', '')),
            'ticket_url': str(metadata.get('ticket_url', '')),
            'source_url': str(metadata.get('source_url', '')),
            'event_card': str(metadata.get('event_card', '')),
            'audience': str(metadata.get('audience', '')),
            'language': str(metadata.get('language', '')),
            'type': 'event'
        }
        
        # Ajout des champs de location à plat
        if location := metadata.get('location', {}):
            formatted.update({
                'venue': str(location.get('name', '')),
                'address': str(location.get('address', '')),
                'latitude': float(location.get('latitude', 0)),
                'longitude': float(location.get('longitude', 0))
            })
        
        return formatted

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def upsert_batch(self, vectors: List[tuple]):
        """Upsert avec retry exponentiel"""
        try:
            return self.index.upsert(vectors=vectors)
        except Exception as e:
            print(f"⚠️ Tentative de retry après erreur: {str(e)}")
            raise e

    def load_data(self, npz_path: str, json_path: str):
        """Charge les embeddings et métadonnées"""
        print("📂 Chargement des données...")
        
        embeddings = np.load(npz_path)['embeddings']
        print(f"✓ {len(embeddings)} embeddings chargés")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        print(f"✓ {len(metadata)} métadonnées chargées")
        
        return embeddings, metadata

    def upsert_events(self, embeddings_path: str, metadata_path: str, batch_size: int = 10) -> bool:
        print("🚀 Démarrage de l'indexation Pinecone")
        
        try:
            embeddings, metadata = self.load_data(embeddings_path, metadata_path)
            if len(embeddings) != len(metadata):
                raise ValueError("Nombre d'embeddings et métadonnées différent")
            
            initial_count = self.index.describe_index_stats().total_vector_count
            print(f"\n📊 Vecteurs existants: {initial_count}")
            
            successful = 0
            failed = 0
            
            for i in tqdm(range(0, len(embeddings), batch_size), desc="↗️ Indexation"):
                batch_vectors = []
                for j in range(i, min(i + batch_size, len(embeddings))):
                    try:
                        formatted_metadata = self.format_metadata(metadata[j])
                        vector_data = (
                            str(metadata[j]['uuid']),  # Utilisation de l'UUID comme clé unique
                            embeddings[j].tolist(),
                            formatted_metadata
                        )
                        batch_vectors.append(vector_data)
                    except Exception as e:
                        print(f"\n❌ Erreur format event {j}: {str(e)}")
                        failed += 1
                        continue
                
                if batch_vectors:
                    try:
                        self.upsert_batch(batch_vectors)
                        successful += len(batch_vectors)
                        print(f"\n✓ Batch {i//batch_size} réussi: {len(batch_vectors)} events")
                    except Exception as e:
                        print(f"\n❌ Erreur batch {i//batch_size}: {str(e)}")
                        failed += len(batch_vectors)
                        continue

            final_count = self.index.describe_index_stats().total_vector_count
            print("\n📊 Résultats:")
            print(f"✓ Indexés: {successful}")
            print(f"✗ Échoués: {failed}")
            print(f"📈 Total vecteurs: {final_count}")
            
            self._test_index(embeddings[0])
            
            return True

        except Exception as e:
            print(f"\n❌ Erreur: {str(e)}")
            return False

    def _test_index(self, test_vector: np.ndarray):
        """Test rapide de l'index"""
        print("\n🔍 Test de l'index...")
        try:
            results = self.index.query(
                vector=test_vector.tolist(),
                top_k=1,
                include_metadata=True
            )
            
            if results.matches:
                print("✓ Test réussi")
                match = results.matches[0]
                print(f"Premier résultat: {match.metadata.get('title', 'Sans titre')}")
            else:
                print("⚠️ Aucun résultat")
                
        except Exception as e:
            print(f"❌ Erreur test: {str(e)}")

if __name__ == "__main__":
    load_dotenv()
    
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    if not PINECONE_API_KEY:
        raise ValueError("API key manquante dans .env")
        
    INDEX_NAME = "lavitrine"
    
    EMBEDDINGS_PATH = f"../data/embeddings/{TODAY}/embeddings_{TODAY}.npz"
    METADATA_PATH = f"../data/embeddings/{TODAY}/metadata_{TODAY}.json"
    
    indexer = EventIndexer(PINECONE_API_KEY, INDEX_NAME)
    
    # Charger les embeddings et metadata
    embeddings = np.load(EMBEDDINGS_PATH)['embeddings']
    with open(METADATA_PATH, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Ne garder que les 10 premiers
    embeddings = embeddings[:10]
    metadata = metadata[:10]
    
    # Sauvegarder temporairement
    temp_emb_path = f"../data/embeddings/{TODAY}/temp_embeddings.npz"
    temp_meta_path = f"../data/embeddings/{TODAY}/temp_metadata.json"
    
    np.savez_compressed(temp_emb_path, embeddings=embeddings)
    with open(temp_meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    success = indexer.upsert_events(temp_emb_path, temp_meta_path)
    
    # Nettoyer les fichiers temporaires
    os.remove(temp_emb_path)
    os.remove(temp_meta_path)
    
    print("\n✨ Indexation des 10 premiers vecteurs terminée" if success else "\n⚠️ Indexation incomplète")