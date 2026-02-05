const API_URL = "http://localhost:5000/api";

export const api = {
  // Récupérer les annonces pour la carte
  getListings: async () => {
    try {
      const response = await fetch(`${API_URL}/listings`);
      if (!response.ok) throw new Error("Erreur listings");
      return await response.json();
    } catch (error) {
      console.error("❌ Erreur Listings:", error);
      return [];
    }
  },

  // Prédiction ML (Feature existante)
  getPrediction: async (searchData) => {
    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(searchData),
      });
      if (!response.ok) throw new Error("Erreur serveur Oracle");
      return await response.json();
    } catch (error) {
      console.error("❌ Erreur API Predict:", error);
      throw error;
    }
  },

  // SCAN QUARTIER
  getQuartierStats: async (quartierName, typeLocal = 'Tout') => {
    try {
      const response = await fetch(`${API_URL}/quartier-stats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          quartier: quartierName,
          type_local: typeLocal
        }),
      });
      
      if (!response.ok) throw new Error("Erreur scan quartier");
      return await response.json();
    } catch (error) {
      console.error("❌ Erreur Scan:", error);
      throw error;
    }
  },

  // Chatbot (MODIFIÉ POUR MARCHER AVEC CHATORACLE.JSX)
  sendChatMessage: async (message, context = null) => {
    try {
      const payload = { message };
      if (context) payload.context = context;
      
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) throw new Error(`Erreur HTTP ${response.status}`);
      
      const data = await response.json();
      return data.response; // <--- ICI : On renvoie seulement le texte, pas l'objet JSON
      
    } catch (error) {
      console.error("❌ Erreur Chat:", error);
      throw error; // On renvoie l'erreur au composant pour qu'il affiche l'alerte rouge
    }
  }
};