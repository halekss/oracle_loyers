"""
Système d'Agent Intelligent - Le chatbot peut utiliser le ML automatiquement.
"""

import re
from typing import Dict, Optional, List

class SmartAgent:
    """
    Agent qui analyse les questions et décide quand utiliser le ML.
    """
    
    def __init__(self, ml_predictor, df_data):
        self.ml_predictor = ml_predictor  # Fonction predict_price_ml
        self.df_data = df_data  # DataFrame des annonces
        
    def analyze_question(self, message: str) -> Dict:
        """
        Analyse la question et détermine quelle action prendre.
        
        Returns:
            {
                'intent': 'predict' | 'compare' | 'general' | 'off_topic',
                'extracted_data': {...},
                'action': 'ml_predict' | 'search_data' | 'chat_only'
            }
        """
        message_lower = message.lower()
        
        # INTENT 1 : Demande de prix / estimation
        if self._is_price_request(message_lower):
            extracted = self._extract_price_request_data(message)
            return {
                'intent': 'predict',
                'extracted_data': extracted,
                'action': 'ml_predict' if extracted['surface'] and extracted['quartier'] else 'need_more_info'
            }
        
        # INTENT 2 : Comparaison de quartiers
        elif self._is_comparison_request(message_lower):
            quartiers = self._extract_quartiers(message)
            return {
                'intent': 'compare',
                'extracted_data': {'quartiers': quartiers},
                'action': 'search_data'
            }
        
        # INTENT 3 : Recherche dans les données
        elif self._is_data_search(message_lower):
            filters = self._extract_filters(message)
            return {
                'intent': 'search',
                'extracted_data': filters,
                'action': 'search_data'
            }
        
        # INTENT 4 : Hors sujet
        elif self._is_off_topic(message_lower):
            return {
                'intent': 'off_topic',
                'extracted_data': {},
                'action': 'chat_only'
            }
        
        # INTENT 5 : Conversation générale
        else:
            return {
                'intent': 'general',
                'extracted_data': {},
                'action': 'chat_only'
            }
    
    def execute_action(self, intent_result: Dict, message: str) -> Dict:
        """
        Exécute l'action déterminée par l'analyse.
        
        Returns:
            {
                'context': str,  # Contexte enrichi pour le LLM
                'data': dict     # Données brutes pour le frontend
            }
        """
        action = intent_result['action']
        
        if action == 'ml_predict':
            return self._execute_ml_prediction(intent_result['extracted_data'])
        
        elif action == 'search_data':
            return self._execute_data_search(intent_result['extracted_data'])
        
        elif action == 'need_more_info':
            return self._build_clarification_context(intent_result['extracted_data'])
        
        else:
            return {'context': '', 'data': {}}
    
    # ============= DÉTECTION D'INTENTIONS =============
    
    def _is_price_request(self, message: str) -> bool:
        """Détecte une demande de prix"""
        keywords = [
            'combien', 'prix', 'loyer', 'coût', 'coute',
            'cher', 'estimat', 'budget', 'payer'
        ]
        return any(kw in message for kw in keywords)
    
    def _is_comparison_request(self, message: str) -> bool:
        """Détecte une demande de comparaison"""
        keywords = ['comparer', 'comparaison', 'vs', 'différence', 'mieux', 'ou']
        return any(kw in message for kw in keywords)
    
    def _is_data_search(self, message: str) -> bool:
        """Détecte une recherche dans les données"""
        keywords = ['trouve', 'cherche', 'montre', 'liste', 'appartement', 'bien']
        return any(kw in message for kw in keywords)
    
    def _is_off_topic(self, message: str) -> bool:
        """Détecte hors sujet"""
        off_topic = [
            'restaurant', 'manger', 'météo', 'politique',
            'football', 'cinéma', 'recette', 'blague'
        ]
        return any(kw in message for kw in off_topic)
    
    # ============= EXTRACTION DE DONNÉES =============
    
    def _extract_price_request_data(self, message: str) -> Dict:
        """
        Extrait surface, quartier, type de bien d'une question.
        
        Exemples:
        - "Combien coûte un 45m² à la Croix-Rousse ?"
        - "Prix d'un T2 à Vaise"
        """
        data = {
            'surface': None,
            'quartier': None,
            'type_bien': None
        }
        
        # Extraire la surface
        surface_match = re.search(r'(\d+)\s*m[²2]', message.lower())
        if surface_match:
            data['surface'] = int(surface_match.group(1))
        else:
            # Essayer de détecter T1, T2, etc.
            type_match = re.search(r'\b(t|f)([1-5])\b', message.lower())
            if type_match:
                type_num = int(type_match.group(2))
                # Estimation surface moyenne par type
                surface_estimates = {1: 25, 2: 45, 3: 65, 4: 85, 5: 100}
                data['surface'] = surface_estimates.get(type_num, 50)
                data['type_bien'] = f"T{type_num}"
        
        # Extraire le quartier
        quartiers = self._extract_quartiers(message)
        if quartiers:
            data['quartier'] = quartiers[0]  # Prendre le premier mentionné
        
        return data
    
    def _extract_quartiers(self, message: str) -> List[str]:
        """Extrait les quartiers mentionnés"""
        quartier_keywords = {
            "croix-rousse": "Croix-Rousse",
            "croix rousse": "Croix-Rousse",
            "presqu'île": "Presqu'île",
            "bellecour": "Presqu'île",
            "vieux lyon": "Vieux-Lyon",
            "part-dieu": "Part-Dieu",
            "guillotière": "Guillotière",
            "vaise": "Vaise",
            "gerland": "Gerland",
            "tête d'or": "Tête d'Or",
            "monplaisir": "Monplaisir",
        }
        
        message_lower = message.lower()
        found = []
        
        for keyword, quartier in quartier_keywords.items():
            if keyword in message_lower:
                found.append(quartier)
        
        return list(set(found))
    
    def _extract_filters(self, message: str) -> Dict:
        """Extrait des filtres de recherche"""
        filters = {}
        
        # Budget max
        budget_match = re.search(r'(\d+)\s*€', message)
        if budget_match:
            filters['max_price'] = int(budget_match.group(1))
        
        # Type de bien
        if 't1' in message.lower() or 'studio' in message.lower():
            filters['type'] = 'Studio/T1'
        elif 't2' in message.lower():
            filters['type'] = 'T2'
        elif 't3' in message.lower():
            filters['type'] = 'T3'
        
        return filters
    
    # ============= EXÉCUTION DES ACTIONS =============
    
    def _execute_ml_prediction(self, extracted_data: Dict) -> Dict:
        """
        Déclenche une prédiction ML automatique.
        """
        surface = extracted_data['surface']
        quartier = extracted_data['quartier']
        
        # Récupérer les coordonnées du quartier
        coords = self._get_quartier_coordinates(quartier)
        
        if not coords:
            return {
                'context': f"Quartier '{quartier}' non trouvé dans la base.",
                'data': {}
            }
        
        # Prédiction ML
        prediction = self.ml_predictor(surface, coords['lat'], coords['lon'])
        
        if not prediction:
            return {
                'context': "Erreur lors de la prédiction ML.",
                'data': {}
            }
        
        # Construire le contexte pour le LLM
        context = f"""
🔮 PRÉDICTION ML AUTOMATIQUE:
Pour un {surface}m² à {quartier}:
- Loyer estimé: {prediction['estimated_price']} €
- Prix au m²: {prediction['prix_m2']} €/m²
- Méthode: {prediction['method']}

INSTRUCTION: Commente cette estimation avec ton style cynique. 
Dis si c'est cher/raisonnable pour le quartier (compare avec les autres quartiers de Lyon).
"""
        
        return {
            'context': context,
            'data': prediction
        }
    
    def _execute_data_search(self, extracted_data: Dict) -> Dict:
        """
        Cherche dans les données réelles.
        """
        if 'quartiers' in extracted_data:
            # Comparaison de quartiers
            quartiers = extracted_data['quartiers']
            comparison = self._compare_quartiers(quartiers)
            
            context = f"""
📊 COMPARAISON DES QUARTIERS:
{comparison}

INSTRUCTION: Résume les différences principales en 3-4 phrases cash.
"""
            return {'context': context, 'data': comparison}
        
        else:
            # Recherche avec filtres
            results = self._search_listings(extracted_data)
            
            context = f"""
🔍 RÉSULTATS DE RECHERCHE:
Trouvé {len(results)} biens correspondants.
{self._format_results(results[:5])}

INSTRUCTION: Commente brièvement ces résultats.
"""
            return {'context': context, 'data': results}
    
    def _build_clarification_context(self, extracted_data: Dict) -> Dict:
        """
        Demande des clarifications manquantes.
        """
        missing = []
        if not extracted_data.get('surface'):
            missing.append("la surface (ex: 45m² ou T2)")
        if not extracted_data.get('quartier'):
            missing.append("le quartier (ex: Croix-Rousse)")
        
        context = f"""
ℹ️ INFORMATIONS MANQUANTES:
Il me manque: {', '.join(missing)}

INSTRUCTION: Demande gentiment ces infos à l'utilisateur (style Oracle).
"""
        
        return {'context': context, 'data': {}}
    
    # ============= HELPERS =============
    
    def _get_quartier_coordinates(self, quartier: str) -> Optional[Dict]:
        """
        Trouve les coordonnées moyennes d'un quartier dans le dataset.
        """
        if self.df_data.empty:
            return None
        
        # Filtrer les annonces du quartier (recherche floue)
        mask = self.df_data['ville'].str.contains(quartier, case=False, na=False)
        subset = self.df_data[mask]
        
        if subset.empty:
            return None
        
        return {
            'lat': subset['latitude'].mean(),
            'lon': subset['longitude'].mean()
        }
    
    def _compare_quartiers(self, quartiers: List[str]) -> str:
        """Compare plusieurs quartiers"""
        comparison = ""
        
        for q in quartiers:
            subset = self.df_data[self.df_data['ville'].str.contains(q, case=False, na=False)]
            if not subset.empty:
                avg_price = subset['prix'].mean()
                avg_m2 = subset['prix_m2'].mean()
                comparison += f"{q}: {avg_price:.0f}€ loyer moyen ({avg_m2:.0f}€/m²)\n"
        
        return comparison
    
    def _search_listings(self, filters: Dict) -> List[Dict]:
        """Cherche des annonces selon des filtres"""
        df = self.df_data.copy()
        
        if 'max_price' in filters:
            df = df[df['prix'] <= filters['max_price']]
        
        if 'type' in filters:
            df = df[df['type_local'] == filters['type']]
        
        return df.head(10).to_dict('records')
    
    def _format_results(self, results: List[Dict]) -> str:
        """Formate les résultats pour le prompt"""
        formatted = ""
        for r in results:
            formatted += f"- {r.get('type_local', '?')} {r['surface']}m² à {r.get('ville', 'Lyon')}: {r['prix']}€\n"
        return formatted