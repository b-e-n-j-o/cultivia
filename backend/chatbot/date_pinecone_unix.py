from pinecone import Pinecone
from datetime import datetime
import pytz
import os
from dotenv import load_dotenv
from tqdm import tqdm
import logging
from typing import Optional, Dict, Any, List

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_pinecone(api_key: str) -> Pinecone:
    """Initialise la connexion à Pinecone"""
    try:
        logger.info("Initialisation de la connexion à Pinecone...")
        pc = Pinecone(api_key=api_key)
        logger.info("Connexion Pinecone établie avec succès")
        return pc
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de Pinecone: {str(e)}")
        raise

def convert_iso_to_unix(date_iso: Optional[str]) -> Optional[int]:
    """
    Convertit une date ISO (YYYY-MM-DD) en timestamp Unix
    en tenant compte du fuseau horaire de Montréal
    
    Args:
        date_iso: Date au format ISO ou None
        
    Returns:
        Optional[int]: Timestamp Unix ou None si la conversion échoue
    """
    if not date_iso or date_iso == "None" or date_iso.strip() == "":
        logger.debug(f"Date ISO invalide reçue: {date_iso}")
        return None
        
    try:
        # Définir le fuseau horaire de Montréal
        montreal_tz = pytz.timezone('America/Montreal')
        
        # Parser la date ISO et ajouter minuit comme heure
        date_obj = datetime.strptime(date_iso, '%Y-%m-%d')
        
        # Localiser la date dans le fuseau horaire de Montréal
        local_date = montreal_tz.localize(date_obj)
        
        # Convertir en timestamp Unix
        unix_timestamp = int(local_date.timestamp())
        
        logger.debug(f"Conversion réussie: {date_iso} -> {unix_timestamp}")
        return unix_timestamp
        
    except ValueError as e:
        logger.warning(f"Format de date invalide pour {date_iso}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la conversion de la date {date_iso}: {str(e)}")
        return None

def process_vector_batch(batch: List[Dict], index) -> int:
    """
    Traite un lot de vecteurs et effectue les mises à jour avec gestion de la taille
    
    Returns:
        int: Nombre de vecteurs mis à jour avec succès
    """
    batch_updates = []
    updated_count = 0
    sub_batch_size = 20  # Taille réduite pour éviter les erreurs de taille
    
    for vector in batch:
        try:
            metadata = vector.metadata
            if not metadata.get('date_iso'):
                continue
                
            unix_timestamp = convert_iso_to_unix(metadata['date_iso'])
            if unix_timestamp is not None:
                metadata['date_unix'] = unix_timestamp
                batch_updates.append({
                    'id': vector.id,
                    'values': vector.values,
                    'metadata': metadata
                })
                
                # Si on atteint la taille du sous-lot, on fait la mise à jour
                if len(batch_updates) >= sub_batch_size:
                    try:
                        index.upsert(vectors=batch_updates)
                        updated_count += len(batch_updates)
                        logger.info(f"Sous-lot de {len(batch_updates)} vecteurs mis à jour")
                        batch_updates = []  # Réinitialiser pour le prochain sous-lot
                    except Exception as e:
                        logger.error(f"Erreur lors de la mise à jour du sous-lot: {str(e)}")
                        # On continue avec le prochain sous-lot même en cas d'erreur
                        batch_updates = []
                
        except AttributeError as e:
            logger.warning(f"Erreur d'attribut sur le vecteur: {str(e)}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement du vecteur: {str(e)}")
    
    # Traiter les vecteurs restants
    if batch_updates:
        try:
            index.upsert(vectors=batch_updates)
            updated_count += len(batch_updates)
            logger.info(f"Dernier sous-lot de {len(batch_updates)} vecteurs mis à jour")
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du dernier sous-lot: {str(e)}")
            
    return updated_count

def process_vectors(index, batch_size: int = 100) -> Dict[str, int]:
    """
    Récupère et traite les vecteurs de l'index Pinecone
    
    Returns:
        Dict[str, int]: Statistiques du traitement
    """
    stats = {
        'total_vectors': 0,
        'processed_vectors': 0,
        'updated_vectors': 0,
        'error_count': 0
    }
    
    try:
        # Récupération des vecteurs
        vectors = index.query(
            vector=[0] * 1536,
            top_k=10000,
            include_metadata=True,
            include_values=True
        )
        
        stats['total_vectors'] = len(vectors.matches)
        logger.info(f"Récupération de {stats['total_vectors']} vecteurs")
        
        # Traitement par lots
        for i in range(0, len(vectors.matches), batch_size):
            batch = vectors.matches[i:i + batch_size]
            stats['processed_vectors'] += len(batch)
            
            with tqdm(total=len(batch), desc=f"Lot {i//batch_size + 1}") as pbar:
                updated = process_vector_batch(batch, index)
                stats['updated_vectors'] += updated
                pbar.update(len(batch))
                
    except Exception as e:
        logger.error(f"Erreur lors du traitement des vecteurs: {str(e)}")
        stats['error_count'] += 1
        
    return stats

def main():
    try:
        load_dotenv()
        
        # Configuration
        api_key = os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX_NAME")
        
        if not api_key or not index_name:
            raise ValueError("Variables d'environnement manquantes")
        
        # Initialisation
        pc = init_pinecone(api_key)
        index = pc.Index(index_name)
        
        # Traitement
        stats = process_vectors(index)
        
        # Rapport final
        logger.info("=== Rapport de traitement ===")
        logger.info(f"Total des vecteurs: {stats['total_vectors']}")
        logger.info(f"Vecteurs traités: {stats['processed_vectors']}")
        logger.info(f"Vecteurs mis à jour: {stats['updated_vectors']}")
        logger.info(f"Erreurs rencontrées: {stats['error_count']}")
        
    except Exception as e:
        logger.error(f"Erreur critique: {str(e)}")
        raise

if __name__ == "__main__":
    main()