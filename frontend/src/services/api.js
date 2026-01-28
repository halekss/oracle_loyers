const API_URL = 'http://localhost:5000/api';

export const api = {
  // 1. Récupérer tous les listings (pour la carte globale)
  getListings: async () => {
    try {
      const response = await fetch(`${API_URL}/listings`);
      if (!response.ok) throw new Error('Erreur réseau');
      return await response.json();
    } catch (error) {
      console.error("Erreur getListings:", error);
      return [];
    }
  },

  // 2. Obtenir une prédiction (Prix + Analyse initiale)
  getPrediction: async (data) => {
    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error('Erreur prédiction');
      return await response.json();
    } catch (error) {
      console.error("Erreur getPrediction:", error);
      throw error;
    }
  },

  // 3. NOUVEAU : Discuter avec l'Oracle (Chatbot)
  getChatResponse: async (message) => {
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      });
      if (!response.ok) throw new Error('Erreur chat');
      return await response.json();
    } catch (error) {
      console.error("Erreur Chat:", error);
      return { response: "L'Oracle est silencieux (Erreur API)." };
    }
  }
};