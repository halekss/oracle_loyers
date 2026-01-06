// URL de base de ton backend Python
const API_URL = "http://127.0.0.1:8000";

export const checkHealth = async () => {
  try {
    const response = await fetch(`${API_URL}/`);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Erreur de connexion à l'Oracle:", error);
    return null;
  }
};