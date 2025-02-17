from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import List, Dict, Optional, Tuple
import logging
from dotenv import load_dotenv
import os
from event_retriever import EventIDRetriever
from conversation_manager import ConversationalEventAgent

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de Flask
app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5173"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Accept"],
        "expose_headers": ["Content-Type"]
    }
})

class EventChatbot:
    def __init__(self, openai_api_key: str, pinecone_api_key: str, index_name: str):
        """
        Initialise le chatbot avec le retriever et l'agent conversationnel.
        """
        self.retriever = EventIDRetriever(
            openai_api_key=openai_api_key,
            pinecone_api_key=pinecone_api_key,
            index_name=index_name
        )
        self.conversation_agent = ConversationalEventAgent(openai_api_key)
        logger.info("EventChatbot initialisé avec succès")

    def process_query(self, user_query: str) -> Tuple[str, List[Dict], Optional[str], Dict]:
        """
        Traite une requête utilisateur et retourne une réponse avec les résultats enrichis.
        """
        try:
            logger.info(f"Traitement de la requête: {user_query}")
            
            # Recherche d'événements avec reformulation
            all_events, top_events, target_date = self.retriever.search(user_query)
            
            # Récupération des détails de reformulation pour l'affichage
            query_analysis = self.retriever.query_rephraser.analyze_query(user_query)
            
            if not all_events:
                response = "Je suis désolé, je n'ai pas trouvé d'événements correspondant à ta recherche. Peux-tu reformuler ta demande ou essayer avec une autre date ?"
                return response, [], target_date, self._format_query_details(query_analysis)

            return "", all_events, target_date, self._format_query_details(query_analysis)

        except Exception as e:
            logger.error(f"Erreur lors du traitement de la requête: {str(e)}", exc_info=True)
            return "Désolé, j'ai rencontré une erreur lors du traitement de ta demande.", [], None, {}

    def _format_query_details(self, query_analysis) -> Dict:
        """
        Formate les détails de l'analyse de la requête pour l'affichage.
        """
        return {
            "reformulations": query_analysis.reformulations,
            "disciplines": query_analysis.disciplines
        }

# Initialisation du chatbot
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "lavitrine"

try:
    chatbot = EventChatbot(
        openai_api_key=OPENAI_API_KEY,
        pinecone_api_key=PINECONE_API_KEY,
        index_name=INDEX_NAME
    )
    logger.info("Chatbot initialized successfully")
except Exception as e:
    logger.error(f"Error initializing chatbot: {str(e)}")
    raise

@app.route('/search', methods=['POST'])
def search():
    logger.info("Received request to /search")
    try:
        data = request.json
        user_message = data.get('message')
        
        if not user_message:
            logger.warning("No message provided in request")
            return jsonify({'error': 'No message provided'}), 400

        # Utilisation du chatbot pour la recherche
        response, events, target_date, query_details = chatbot.process_query(user_message)
        
        # Formatage de la réponse
        response_data = {
            'events': events,
            'prompt_events': events[:5],  # Prendre les 5 premiers événements pour le prompt
            'target_date': target_date,
            'status': 'success'
        }
        
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        return jsonify({
            'error': str(e),
            'status': 'error',
            'events': [],
            'prompt_events': []
        }), 500

@app.route('/chat', methods=['POST'])
def chat():
    logger.info("Received request to /chat")
    try:
        data = request.json
        user_message = data.get('message')
        prompt_events = data.get('prompt_events', [])
        target_date = data.get('target_date')
        
        if not user_message:
            logger.warning("Missing message in chat request")
            return jsonify({
                'error': 'Message missing',
                'status': 'error'
            }), 400

        # Génération de la réponse avec l'agent conversationnel
        response = chatbot.conversation_agent.generate_response(
            events=prompt_events,
            user_query=user_message,
            target_date=target_date
        )
        
        return jsonify({
            'message': response,
            'status': 'success'
        })

    except Exception as e:
        logger.error(f"Error generating chat response: {str(e)}", exc_info=True)
        return jsonify({
            'error': str(e),
            'status': 'error',
            'message': "Je suis désolé, je n'ai pas pu générer une réponse appropriée."
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, port=5003, host='0.0.0.0')

"""
Architecture et Fonctionnalités Avancées d'un Chatbot Culturel

Ce système représente une implémentation sophistiquée d'un chatbot spécialisé dans la recherche 
et la recommandation d'événements culturels, avec plusieurs caractéristiques techniques notables :

1. Architecture Modulaire et Spécialisée
- Séparation claire des responsabilités entre différents modules :
  * QueryRephraser : Analyse sémantique et reformulation intelligente des requêtes
  * DateExtractor : Extraction et normalisation des informations temporelles
  * EventRetriever : Recherche vectorielle et filtrage des événements
  * ConversationManager : Génération de réponses naturelles et contextuelles

2. Traitement Intelligent des Requêtes
- Analyse multi-niveaux des intentions utilisateur :
  * Reformulation sémantique pour optimiser la recherche
  * Catégorisation automatique par disciplines artistiques
  * Extraction contextuelle des dates avec gestion des fuseaux horaires
  * Support des intervalles de dates et expressions temporelles relatives

3. Recherche Vectorielle Avancée
- Utilisation de Pinecone pour la recherche sémantique :
  * Embeddings OpenAI pour la vectorisation des requêtes
  * Filtres composites (dates + disciplines)
  * Dédoublonnage intelligent des résultats
  * Tri et regroupement des événements similaires

4. Gestion Temporelle Sophistiquée
- Système robuste de gestion des dates :
  * Support du fuseau horaire de Montréal
  * Conversion ISO-Unix pour optimisation des requêtes
  * Gestion des intervalles et dates multiples
  * Normalisation des formats temporels

5. Bonnes Pratiques de Développement
- Logging extensif pour monitoring et debugging
- Gestion des erreurs à tous les niveaux
- Type hints pour la sécurité du code
- Documentation détaillée des fonctions
- Tests unitaires intégrés
- Variables d'environnement pour la configuration

6. Optimisations de Performance
- Mise en cache des embeddings
- Batching des requêtes API
- Limitation intelligente des résultats
- Dédoublonnage optimisé

7. Expérience Utilisateur
- Réponses naturelles et contextuelles
- Suggestions pertinentes basées sur le contexte
- Support multilingue (français)
- Gestion des cas d'erreur avec feedback utilisateur

Exemple d'Utilisation :
Query: "Je cherche une activité culturelle ce weekend avec mes enfants"
1. Analyse et reformulation :
   - "activités familiales et culturelles samedi dimanche"
   - "spectacles jeune public weekend"
   - "événements famille musée exposition weekend"
2. Extraction temporelle : prochain weekend
3. Catégorisation : Théâtre, Cirque, Musée
4. Recherche vectorielle avec filtres
5. Génération réponse naturelle avec suggestions contextuelles

Technologies : Python 3.8+, OpenAI GPT-3.5, Pinecone, PyTZ, Logging, Dotenv
"""