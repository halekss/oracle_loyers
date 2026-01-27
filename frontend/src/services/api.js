const API_URL = "http://localhost:5000/api";

export const api = {
  // 1. Récupérer l'estimation (POST)
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
      console.error("Erreur API:", error);
      throw error;
    }
  },

  // 2. Récupérer les listings pour la carte (GET)
  getListings: async () => {
    try {
      const response = await fetch(`${API_URL}/listings`);
      if (!response.ok) throw new Error("Erreur listings");
      return await response.json();
    } catch (error) {
      console.error("Erreur Listings:", error);
      return [];
    }
  },
};