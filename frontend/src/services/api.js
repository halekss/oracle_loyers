const DEFAULT_API_URL = "http://localhost:5000/api";
const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", ""]);

// Distingue les erreurs réseau (backend injoignable) des réponses HTTP
// 4xx/5xx, pour que l'UI puisse afficher un message adapté à chaque cas
// plutôt qu'un message générique unique.
export class ApiError extends Error {
  constructor(message, { type = "unknown", status = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.type = type; // "network" | "rate_limit" | "client" | "server" | "unknown"
    this.status = status;
  }
}

const classifyResponseError = (response) => {
  if (response.status === 429) {
    return new ApiError("Trop de requêtes (429)", { type: "rate_limit", status: response.status });
  }
  if (response.status >= 500) {
    return new ApiError(`Erreur serveur (${response.status})`, { type: "server", status: response.status });
  }
  if (response.status >= 400) {
    return new ApiError(`Requête invalide (${response.status})`, { type: "client", status: response.status });
  }
  return new ApiError(`Réponse inattendue (${response.status})`, { type: "unknown", status: response.status });
};

const fetchWithClassification = async (url, options) => {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new ApiError("Impossible de contacter le serveur (problème réseau).", { type: "network" });
  }

  if (!response.ok) throw classifyResponseError(response);

  return response;
};

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

// Message neutre adapté au type d'erreur, pour l'UI générale (bannières d'erreur).
export const describeApiError = (error) => {
  if (error instanceof ApiError) {
    switch (error.type) {
      case "network":
        return "Impossible de contacter le serveur. Vérifiez votre connexion et réessayez.";
      case "rate_limit":
        return "Trop de requêtes envoyées. Patientez un instant avant de réessayer.";
      case "client":
        return "La requête envoyée est invalide.";
      case "server":
        return "Le serveur rencontre un problème. Réessayez dans quelques instants.";
      default:
        return "Une erreur inattendue est survenue.";
    }
  }
  return "Une erreur inattendue est survenue.";
};

export const api = {
  // Liste paginée des annonces — GET /api/annonces (ORA-84)
  getAnnonces: async ({ ville, quartier, page = 1, perPage = 20 } = {}) => {
    try {
      const params = new URLSearchParams();
      if (ville) params.set('ville', ville);
      if (quartier) params.set('quartier', quartier);
      params.set('page', page);
      params.set('per_page', perPage);

      const response = await fetchWithClassification(`${API_URL}/annonces?${params.toString()}`);

      return await response.json();
    } catch (error) {
      console.error("❌ Erreur Annonces:", error);
      throw error;
    }
  },

  // Annonces avec coordonnées (toutes, non paginées) — GET /api/listings.
  // Utilisé pour calculer la bounding-box carte des résultats filtrés (ORA-105).
  getListings: async () => {
    try {
      const response = await fetchWithClassification(`${API_URL}/listings`);

      return await response.json();
    } catch (error) {
      console.error("❌ Erreur Listings:", error);
      throw error;
    }
  },

  // Journalise un clic sortant vers l'annonce source — POST /api/annonces/:id/click (ORA-91)
  logAnnonceClick: async (annonceId) => {
    try {
      const response = await fetchWithClassification(`${API_URL}/annonces/${annonceId}/click`, {
        method: 'POST',
      });

      return await response.json();
    } catch (error) {
      console.error("❌ Erreur tracking clic annonce:", error);
      throw error;
    }
  },

  // SCAN QUARTIER
  getQuartierStats: async (quartierName, typeLocal = 'Tout') => {
    try {
      const response = await fetchWithClassification(`${API_URL}/quartier-stats`, {
        ...apiFetchOptions({
          quartier: quartierName,
          type_local: typeLocal
        }),
      });

      return await response.json();
    } catch (error) {
      console.error("❌ Erreur Scan:", error);
      throw error;
    }
  },

  // Historique du prix moyen/m² par quartier — /api/quartier-historique
  getQuartierHistorique: async (quartierName, typeLocal = 'Tout') => {
    try {
      const response = await fetchWithClassification(`${API_URL}/quartier-historique`, {
        ...apiFetchOptions({
          quartier: quartierName,
          type_local: typeLocal
        }),
      });

      return await response.json();
    } catch (error) {
      console.error("❌ Erreur Historique:", error);
      throw error;
    }
  },

  // Prédiction ML (XGBoost) — /api/predict
  predict: async ({ surface, quartier, type_local, type = undefined }) => {
    try {
      const payload = { surface, quartier, type_local };
      if (type) payload.type = type;

      const response = await fetchWithClassification(`${API_URL}/predict`, {
        ...apiFetchOptions(payload),
      });

      return await response.json();
    } catch (error) {
      console.error("❌ Erreur Predict:", error);
      throw error;
    }
  },

  // Chatbot Immotep
  sendChatMessage: async (message, context = null) => {
    try {
      const payload = { message };
      if (context) payload.context = context;

      const response = await fetchWithClassification(`${API_URL}/chat`, {
        ...apiFetchOptions(payload),
      });

      return await response.json();
    } catch (error) {
      console.error("❌ Erreur Chat:", error);
      throw error;
    }
  }
};
