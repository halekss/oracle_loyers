const API_URL = "http://localhost:5000/api";

export const api = {
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

  // 👇 FONCTION CHAT MODIFIÉE : Accepte maintenant un contexte optionnel
  sendChatMessage: async (message, context = null) => {
    try {
      console.log("📤 Envoi message:", message);
      if (context) {
        console.log("📊 Avec contexte ML");
      }
      
      // Construction du payload
      const payload = { message };
      
      // Si un contexte est fourni (résultat du ML), on l'ajoute
      if (context) {
        payload.context = context;
      }
      
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) {
        throw new Error(`Erreur HTTP ${response.status}`);
      }
      
      const data = await response.json();
      console.log("📥 Réponse reçue:", data.response);
      
      return data.response;
    } catch (error) {
      console.error("❌ Erreur Chat:", error);
      return "🔴 L'Oracle est injoignable. Vérifiez que le backend et LM Studio sont démarrés.";
    }
  },
};