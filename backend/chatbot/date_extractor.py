from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from typing import Optional, List
from openai import OpenAI
import locale
import json
from dotenv import load_dotenv
import os

load_dotenv()

class DateExtraction(BaseModel):
    date_found: bool = Field(description="Indique si une date a été trouvée")
    dates: List[str] = Field(description="Liste des dates au format YYYY-MM-DD", default=[])
    date_type: str = Field(description="Type: explicit, relative, interval, multiple")
    is_interval: bool = Field(description="True si les dates forment un intervalle continu")
    interval_bounds: Optional[dict] = Field(description="Bornes de l'intervalle", default=None)

class DateContextProvider:
    def __init__(self):
        # Configuration de la locale pour la gestion des accents
        try:
            locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_TIME, 'fr_FR')
            except locale.Error:
                pass  # Fallback to default locale if French is not available
        
        self.current_date = datetime.now()
    
    def get_weekend_dates(self) -> List[str]:
        """Retourne les dates du prochain weekend"""
        today = self.current_date
        days_until_saturday = (5 - today.weekday()) % 7
        next_saturday = today + timedelta(days=days_until_saturday)
        next_sunday = next_saturday + timedelta(days=1)
        return [next_saturday.strftime("%Y-%m-%d"), next_sunday.strftime("%Y-%m-%d")]
    
    def get_next_week_dates(self) -> List[str]:
        """Retourne les dates de la semaine prochaine"""
        today = self.current_date
        days_until_monday = (7 - today.weekday()) % 7
        next_monday = today + timedelta(days=days_until_monday)
        dates = []
        for i in range(7):
            date = next_monday + timedelta(days=i)
            dates.append(date.strftime("%Y-%m-%d"))
        return dates

    def get_month_dates(self) -> List[str]:
        """Retourne les dates du mois en cours"""
        today = self.current_date
        first_day = today.replace(day=1)
        if first_day.month == 12:
            next_month = first_day.replace(year=first_day.year + 1, month=1)
        else:
            next_month = first_day.replace(month=first_day.month + 1)
        dates = []
        current = first_day
        while current < next_month:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        return dates
    
    def get_context(self) -> dict:
        """Génère le contexte temporel complet"""
        tomorrow = self.current_date + timedelta(days=1)
        weekend_dates = self.get_weekend_dates()
        next_week_dates = self.get_next_week_dates()
        month_dates = self.get_month_dates()
        
        return {
            "current_date": self.current_date.strftime("%Y-%m-%d"),
            "current_weekday": self.current_date.strftime("%A"),
            "tomorrow": tomorrow.strftime("%Y-%m-%d"),
            "weekend_dates": weekend_dates,
            "next_week_dates": next_week_dates,
            "month_dates": month_dates,
            "current_month": self.current_date.strftime("%B"),
            "current_year": str(self.current_date.year)
        }

class EnhancedDateExtractorChain:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.context_provider = DateContextProvider()

    def extract_date(self, text: str) -> DateExtraction:
        context = self.context_provider.get_context()
        
        messages = [{"role": "system", "content": 
            f"""Analyse le texte pour extraire les dates avec ce contexte :
            Date: {context['current_date']}
            Jour: {context['current_weekday']}
            Mois: {context['current_month']}
            Weekend: {context['weekend_dates']}
            Semaine prochaine: {context['next_week_dates']}
            
            Pour un intervalle ("la semaine prochaine", "du 15 au 20"):
            - is_interval: true
            - interval_bounds: {{start: première_date, end: dernière_date}}
            
            Pour des dates distinctes ("mardi ou jeudi"):
            - is_interval: false
            
            Format: {{
                "date_found": bool,
                "dates": ["YYYY-MM-DD"],
                "date_type": "explicit|relative|interval|multiple",
                "is_interval": bool,
                "interval_bounds": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}} ou null
            }}
            """},
            {"role": "user", "content": text}
        ]

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0
        )
        
        result = json.loads(response.choices[0].message.content)
        return DateExtraction(**result)

# Fonction de test
def test_date_extractor(api_key: str):
    """Fonction de test avec gestion des erreurs"""
    try:
        extractor = EnhancedDateExtractorChain(api_key)
        
        print("\nBienvenue dans le testeur d'extraction de dates!")
        print("Entrez une phrase contenant une date ou 'q' pour quitter")
        
        while True:
            query = input("\nVotre requête: ")
            if query.lower() == 'q':
                break
                
            try:
                result = extractor.extract_date(query)
                print(f"Dates trouvées: {', '.join(result.dates) if result.dates else 'Aucune date'}")
                print(f"Type: {result.date_type}")
                if result.is_interval and result.interval_bounds:
                    print(f"Intervalle: du {result.interval_bounds['start']} au {result.interval_bounds['end']}")
            except Exception as e:
                print(f"Erreur lors du traitement de la requête: {str(e)}")
                
    except Exception as e:
        print(f"Erreur d'initialisation: {str(e)}")

if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Erreur: OPENAI_API_KEY non définie dans les variables d'environnement")
    else:
        test_date_extractor(api_key)