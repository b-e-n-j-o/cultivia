from typing import Dict, List
from dataclasses import dataclass
from openai import OpenAI
import json
import logging
from dotenv import load_dotenv
import os

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QueryAnalysis:
    """Résultat de l'analyse d'une requête"""
    original_query: str
    reformulations: List[str]
    disciplines: List[str]

class QueryRephraser:
    VALID_DISCIPLINES = [
        "Art de la parole",
        "Art visuel",
        "Cinéma",
        "Cirque",
        "Danse",
        "Histoire et Patrimoine",
        "Humour",
        "Musique",
        "Théâtre",
        "Variété",
        "Conférence et atelier",
        "Visite guidée ou animée"
    ]

    def __init__(self):
        """Initialise le QueryRephraser avec la clé API OpenAI depuis les variables d'environnement"""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _create_prompt(self, query: str) -> str:
        """Crée le prompt avec les règles d'interprétation incluses"""
        return f"""Analysez la requête suivante et proposez trois reformulations différentes qui élargissent et enrichissent la recherche.

        Requête originale : "{query}"

        Disciplines disponibles :
        {', '.join(self.VALID_DISCIPLINES)}

        Règles importantes pour l'analyse :
        - Séparéer action et être spectateur, par exemple : "aller danser" et "aller voir un spectacle de danse" ont des intentions différentes.

        Répondez STRICTEMENT dans ce format :
        REFORMULATIONS:
        1. <première reformulation différente mais cohérente>
        2. <deuxième reformulation avec une autre approche et faisant intervenir un possible lieu en rapport avec la requete>
        3. <troisième reformulation avec encore une autre perspective>
        DISCIPLINES:
        1. <discipline la plus probable>
        2. <deuxième discipline probable>
        3. <troisième discipline probable>

        Les reformulations doivent :
        - Être variées mais garder l'intention originale
        - Utiliser des synonymes et expressions alternatives, trouver un lieu ou des mots clés en rapport avec la requete
        - Enrichir la recherche avec différents angles
        - Le plus important : etre adaptées à la recherche d'evennement dans le domaine culturel
        
        Exemple pour "je veux aller danser ce weekend":
        REFORMULATIONS:
        1. soirée dansante bar ou club ce weekend
        2. sortie boîte de nuit pour danser ce weekend
        3. événement dancefloor musique weekend
        """

    def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyse et reformule la requête utilisateur"""
        try:
            logger.info(f"Analyse de la requête: {query}")
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Vous êtes un expert en analyse et reformulation de requêtes culturelles."},
                    {"role": "user", "content": self._create_prompt(query)}
                ],
                temperature=0.7  # Augmenté pour plus de variété dans les reformulations
            )
            
            result_text = response.choices[0].message.content
            reformulations, disciplines = self._parse_response(result_text)
            
            logger.info(f"Reformulations générées: {reformulations}")
            logger.info(f"Disciplines identifiées: {disciplines}")
            
            return QueryAnalysis(
                original_query=query,
                reformulations=reformulations,
                disciplines=disciplines
            )

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse: {str(e)}")
            return QueryAnalysis(
                original_query=query,
                reformulations=[query],
                disciplines=[]
            )

    def _parse_response(self, response: str) -> tuple[List[str], List[str]]:
        """Parse la réponse du LLM pour extraire les reformulations et les disciplines"""
        reformulations = []
        disciplines = []
        
        current_section = None
        
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('REFORMULATIONS:'):
                current_section = 'reformulations'
            elif line.startswith('DISCIPLINES:'):
                current_section = 'disciplines'
            elif line.startswith('1.') or line.startswith('2.') or line.startswith('3.'):
                content = line[3:].strip()
                if current_section == 'reformulations':
                    reformulations.append(content)
                elif current_section == 'disciplines' and content in self.VALID_DISCIPLINES:
                    disciplines.append(content)

        return reformulations[:3], disciplines[:3]  # Assure qu'on a max 3 de chaque

def main():
    """Fonction de test"""
    rephraser = QueryRephraser()
    
    print("\nBienvenue dans le testeur de reformulation de requêtes!")
    print("Entrez 'q' pour quitter")
    
    while True:
        query = input("\nEntrez votre requête: ").strip()
        
        if query.lower() == 'q':
            print("Au revoir!")
            break
            
        if not query:
            print("Requête vide, veuillez réessayer")
            continue
            
        print(f"\nRequête originale: {query}")
        result = rephraser.analyze_query(query)
        print("\nReformulations:")
        for i, ref in enumerate(result.reformulations, 1):
            print(f"{i}. {ref}")
        print(f"\nDisciplines: {result.disciplines}")

if __name__ == "__main__":
    main()