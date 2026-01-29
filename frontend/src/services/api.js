// src/services/api.js
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export const api = {
  /**
   * 🎯 Route SCAN : Obtenir l'estimation ML
   */
  async getPrediction(data) {
    try {
      console.log('📡 API : Envoi de la prédiction...', data);
      
      const response = await fetch(`${API_BASE_URL}/api/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Erreur API ${response.status}: ${errorText}`);
      }
      
      const result = await response.json();
      console.log('✅ API : Prédiction reçue', result);
      
      return result;
    } catch (error) {
      console.error('❌ API : Erreur getPrediction', error);
      throw error;
    }
  },

  /**
   * 🤖 Route CHAT : Envoyer message avec contexte ML optionnel
   * ⚡ FUSION : ml_context sera injecté dans le prompt système côté backend
   */
  async sendChatMessage(message, ml_context = null) {
    try {
      console.log('💬 API : Envoi du message chat...', {
        message: message.substring(0, 50) + '...',
        hasContext: !!ml_context
      });
      
      const payload = {
        message: message,
        ml_context: ml_context  // 🔥 Le contexte ML passe ici
      };

      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ API Chat : Erreur serveur', errorText);
        throw new Error(`Erreur Chat API : ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ API : Réponse chat reçue', data.response.substring(0, 100) + '...');
      
      return data.response;
    } catch (error) {
      console.error('❌ API : Erreur sendChatMessage', error);
      throw error;
    }
  },

  /**
   * 📊 Récupérer les annonces pour la carte
   */
  async getListings() {
    try {
      console.log('📡 API : Récupération des annonces...');
      
      const response = await fetch(`${API_BASE_URL}/api/listings`);
      
      if (!response.ok) {
        throw new Error(`Erreur Listings : ${response.status}`);
      }
      
      const listings = await response.json();
      console.log(`✅ API : ${listings.length} annonces récupérées`);
      
      return listings;
    } catch (error) {
      console.error('❌ API : Erreur getListings', error);
      throw error;
    }
  },

  /**
   * ❤️ Vérifier que le backend est vivant
   */
  async healthCheck() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      
      if (!response.ok) {
        throw new Error(`Backend non disponible : ${response.status}`);
      }
      
      const health = await response.json();
      console.log('✅ Backend Health Check :', health);
      
      return health;
    } catch (error) {
      console.error('❌ Backend Health Check Failed :', error);
      throw error;
    }
  }
};

// 🔥 Health check automatique au chargement
if (import.meta.env.DEV) {
  api.healthCheck().catch(() => {
    console.warn('⚠️ Backend non disponible au démarrage');
  });
}