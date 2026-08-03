const DEFAULT_API_URL = "http://localhost:5000/api";
const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", ""]);

export const getApiBaseUrl = (env = import.meta.env || {}, locationInfo = globalThis.location) => {
  if (!env.VITE_API_URL && !LOCAL_HOSTS.has(locationInfo?.hostname || "")) {
    throw new Error("VITE_API_URL must be configured when the frontend is deployed.");
  }

  const apiUrl = env.VITE_API_URL || DEFAULT_API_URL;
  return apiUrl.replace(/\/+$/, "");
};

const API_URL = getApiBaseUrl();

export const apiFetchOptions = (payload) => ({
  method: "POST",
  headers: { "Content-Type": "text/plain" },
  body: JSON.stringify(payload),
});

export const api = {
  // SCAN QUARTIER
  getQuartierStats: async (quartierName, typeLocal = 'Tout') => {
    try {
      const response = await fetch(`${API_URL}/quartier-stats`, {
        ...apiFetchOptions({
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

  // Chatbot Immotep
  sendChatMessage: async (message, context = null) => {
    try {
      const payload = { message };
      if (context) payload.context = context;
      
      const response = await fetch(`${API_URL}/chat`, {
        ...apiFetchOptions(payload),
      });
      
      if (!response.ok) throw new Error(`Erreur HTTP ${response.status}`);
      
      const data = await response.json();
      return data;
      
    } catch (error) {
      console.error("❌ Erreur Chat:", error);
      throw error;
    }
  }
};
