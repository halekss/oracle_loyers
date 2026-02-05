// On remet le port 5000 ici
const API_URL = "http://localhost:5000/api";

export const api = {
  getListings: async () => {
    try {
      const response = await fetch(`${API_URL}/listings`); 
      if (!response.ok) return [];
      return await response.json();
    } catch (error) {
      console.error("❌ Erreur Listings:", error);
      return [];
    }
  },

  getQuartierStats: async (quartierName, typeLocal = 'Tout') => {
    try {
      const response = await fetch(`${API_URL}/quartier-stats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quartier: quartierName, type_local: typeLocal }),
      });
      if (!response.ok) throw new Error("Erreur scan");
      return await response.json();
    // eslint-disable-next-line no-unused-vars
    } catch (error) {
      return { prix_m2: 0, ambiance: "Inconnue", verdict: "Erreur serveur" };
    }
  },

  sendChatMessage: async (message, history = []) => {
    try {
      const formattedHistory = Array.isArray(history) 
        ? history.filter(msg => msg.text && !msg.text.includes("L'Oracle t'écoute"))
                .map(msg => ({ role: msg.sender === 'oracle' ? 'assistant' : 'user', content: msg.text }))
        : [];

      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message, history: formattedHistory }),
      });
      
      if (!response.ok) throw new Error(`Erreur HTTP ${response.status}`);
      const data = await response.json();
      return data.response; 
    } catch (error) {
      console.error("❌ Erreur Chat:", error);
      return "💤 Immotep dort. (Vérifie que le backend tourne sur le port 5000).";
    }
  }
};