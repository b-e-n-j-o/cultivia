from typing import List, Dict, Optional
from openai import OpenAI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RephraseAgent:
    def __init__(self, client: OpenAI):
        self.client = client
        logger.info("RephraseAgent initialized")
        
    def rephrase_query(self, user_query: str) -> str:
        """
        Reformule la requête utilisateur pour optimiser la recherche sémantique.
        """
        try:
            prompt = f"""Reformule la requête suivante pour optimiser la recherche sémantique d'événements culturels.
            La reformulation doit:
            - Extraire les concepts et thèmes clés
            - Être plus explicite et descriptive
            - Utiliser un vocabulaire riche et varié
            - Garder l'intention originale
            - Être orientée vers la recherche de contenu

            Requête originale: "{user_query}"

            Reformule cette requête en une phrase claire et détaillée."""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Tu es un expert en reformulation de requêtes pour la recherche sémantique."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )

            rephrased_query = response.choices[0].message.content.strip()
            logger.info(f"Requête originale: {user_query} -> Reformulée: {rephrased_query}")
            return rephrased_query

        except Exception as e:
            logger.error(f"Erreur lors de la reformulation: {str(e)}")
            return user_query

class ConversationalEventAgent:
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.rephrase_agent = RephraseAgent(self.client)
        logger.info("ConversationalEventAgent initialized")

    def generate_response(
        self,
        events: List[Dict],
        user_query: str,
        target_date: Optional[str] = None
    ) -> str:
        """
        Génère une réponse conversationnelle basée sur les événements trouvés
        et la requête de l'utilisateur.
        """
        try:
            # Reformulation de la requête
            rephrased_query = self.rephrase_agent.rephrase_query(user_query)
            events_summary = self._format_events_for_prompt(events)
            date_info = f" pour {target_date}" if target_date else ""
            
            # Construire le prompt
            prompt = f"""En tant qu'assistant culturel amical et décontracté, engage une conversation naturelle avec l'utilisateur à propos des événements trouvés.

Question originale de l'utilisateur : "{user_query}"
Question reformulée pour le contexte : "{rephrased_query}"

Événements disponibles{date_info} :
{events_summary}

Directives pour ta réponse :
1. Parle comme dans une vraie conversation, de manière décontractée et amicale
2. Utilise "tu" plutôt que "vous"
3. Tu es un assistant culturel amical et décontracté, tu prends en compte la question utilisateur dans ta reponse
4. Présente les événements de façon naturelle, comme si tu recommandais à un ami
5. Aie comme objectif principal de fournir des suggestions d'événements pertinents et intéressants
6. Évite les listes ou les formats trop structurés, préfère un style conversationnel fluide
7. Ajoute des touches personnelles (ex: "Je pense que tu vas adorer...", "Ce qui est super avec cet événement...")
8. Termine sur une note amicale ou une question ouverte"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Tu es un ami passionné de culture qui adore partager ses découvertes d'événements à Montréal. Tu parles de façon naturelle et enthousiaste, comme dans une vraie conversation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=500
            )

            response_content = response.choices[0].message.content.strip()
            return response_content

        except Exception as e:
            logger.error(f"Erreur lors de la génération de la réponse: {str(e)}")
            return f"Ah, j'ai trouvé {len(events)} événements qui pourraient t'intéresser !"

    def _format_events_for_prompt(self, events: List[Dict]) -> str:
        """Formate les événements de manière simple pour le contexte."""
        formatted_events = []
        
        for i, event in enumerate(events, 1):
            # Gestion des dates multiples
            if isinstance(event.get('date'), list):
                dates = [f"{d} à {t}" for d, t in zip(event.get('date', []), event.get('time', []))]
                date_info = ', '.join(dates)
            else:
                date_info = f"{event.get('date', '')} à {event.get('time', '')}"
            
            event_info = [
                f"Événement {i}:",
                f"Titre: {event.get('title', 'Sans titre')}",
                f"Lieu: {event.get('venue', '')} à {event.get('city', '')}",
                f"Date(s): {date_info}",
                f"Description: {event.get('description', '')}",
                f"Prix: {event.get('price', 'Non spécifié')}",
                "---"
            ]
            formatted_events.append('\n'.join(event_info))

        return '\n'.join(formatted_events)