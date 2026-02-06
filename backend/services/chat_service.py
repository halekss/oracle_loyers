import requests
import sys

class ChatService:
    def __init__(self):
        self.llm_url = "http://host.docker.internal:1234/v1/chat/completions" # IP localhost standard
        self.model_name = "dolphin-2.9.3-mistral-nemo-12b" # Nom du modèle demandé
        
        # Le Prompt Système original d'Immotep
        self.system_prompt = """
        Tu es Immotep, l'agent immobilier le plus désagréable, cynique et hautain de Lyon.
        Ta personnalité : Tu détestes les clients pauvres (des "gueux") et tu méprises les riches qui se font arnaquer (des "pigeons").

        OBJECTIF : Présenter des biens immobiliers ou répondre aux questions de manière FLUIDE et NATURELLE.
        
        RÈGLES DE CONVERSATION :
        1. Oublie les listes à puces et les formats rigides type "NOM : Valeur".
        2. Fais des phrases complètes. Intègre les données (Prix, Quartier, Surface) directement dans tes insultes.
        3. Ton ton doit être mordant, sarcastique et direct.
        
        EXEMPLE DE CE QU'IL FAUT FAIRE :
        "J'ai trouvé un taudis à Gerland pour toi. Ils osent en demander 800€ pour 20m², c'est du vol qualifié mais bon, vu ton budget, tu n'as pas le choix."

        EXEMPLE DE CE QU'IL NE FAUT PAS FAIRE (INTERDIT) :
        "Quartier : Gerland. Prix : 800€. Verdict : C'est cher."

        SI TU PRÉSENTES UN BIEN :
        - Cite toujours le PRIX et le QUARTIER.
        - Moque-toi de la surface si elle est petite ("cage à poules", "placard à balais").
        - Si le prix est élevé, traite l'acheteur de pigeon.
        
        SI RIEN NE CORRESPOND :
        - Dis-lui clairement qu'il est trop pauvre pour Lyon et qu'il devrait chercher à Saint-Etienne.

        Reste bref (3-4 phrases maximum) et percutant. Pas d'emojis.
        """

    def _format_listings(self, df, quartier_filter=None):
        """
        Transforme une partie du DataFrame en string lisible pour l'IA.
        Si un quartier est fourni dans le contexte, on essaie de filtrer.
        """
        liste_compacte = ""
        
        # Filtrage intelligent : si on a un quartier, on prend des annonces de ce quartier
        # Sinon on prend un échantillon aléatoire comme avant
        if quartier_filter and 'quartier' in df.columns:
            # Recherche insensible à la casse
            mask = df['quartier'].str.contains(quartier_filter, case=False, na=False)
            listings = df[mask]
            if len(listings) < 5: # Si pas assez d'annonces, on prend tout le monde
                listings = df
        else:
            listings = df

        # On limite à 40 annonces pour ne pas exploser le contexte
        if len(listings) > 40:
            listings = listings.sample(40)

        for index, row in listings.iterrows():
            try:
                id_a = row.get('id_annonce', index)
                q = str(row.get('quartier', 'Inconnu'))
                p = float(row.get('prix', 0))
                s = float(row.get('surface', 0))
                t = row.get('type_local', '?')
                if p > 0 and s > 0:
                    liste_compacte += f"[ID:{id_a}] {t} | {q} | {p}€ | {s}m²\n"
            except:
                continue
        
        return liste_compacte

    def get_response(self, user_message, context_str, dataframe):
        """
        Génère la réponse d'Immotep.
        - user_message : La question de l'utilisateur
        - context_str : Le résumé envoyé par le frontend (ex: "Quartier: Gerland...")
        - dataframe : Les données brutes pour que l'IA puisse piocher dedans
        """
        
        # 1. Extraction du nom du quartier depuis le contexte (rudimentaire mais efficace)
        quartier_cible = None
        if context_str and "Quartier:" in context_str:
            try:
                # Ex: "Quartier: Gerland, Type..." -> "Gerland"
                partie_q = context_str.split("Quartier:")[1].split(",")[0].strip()
                quartier_cible = partie_q
            except:
                pass

        # 2. Préparation des données immobilières
        data_text = self._format_listings(dataframe, quartier_cible)
        
        # 3. Construction des messages
        # On injecte les données (data_text) et le contexte technique (context_str)
        prompt_utilisateur = f"""
        CONTEXTE ACTUEL (Données du scan) : {context_str}
        
        BASE DE DONNÉES DISPONIBLE (Extraits) :
        {data_text}
        
        QUESTION DU CLIENT :
        "{user_message}"
        
        Réponds en suivant scrupuleusement ton rôle d'Immotep.
        """

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt_utilisateur}
        ]

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.6, # Un peu de créativité pour les insultes
            "max_tokens": 600,
            "stream": False
        }

        try:
            print(f"🤖 Appel LLM ({self.model_name})...")
            reponse = requests.post(self.llm_url, json=payload, timeout=60) # Timeout de sécurité
            
            if reponse.status_code == 200:
                contenu = reponse.json()['choices'][0]['message']['content']
                # Nettoyage léger
                return contenu.replace("ID:", "").replace("[", "").replace("]", "").strip()
            else:
                return f"Erreur API ({reponse.status_code}). Mon génie est incompris."
                
        except Exception as e:
            print(f"❌ Erreur connexion LLM: {e}")
            return "Je ne peux pas répondre. Mon serveur est aussi vide que ton compte en banque."