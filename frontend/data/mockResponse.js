// src/data/mockResponse.js
// Données de secours conformes au Contrat API

export const MOCK_RESULT = {
    score: 50,
    message: "[MODE SECOURS] Le Backend est hors ligne. Données simulées par l'Architecte.",
    estimated_price: 1000,
    price_note: "Estimation par défaut (Backend Down)",
    
    // Structure 'details' obligatoire selon le contrat
    details: {
      kebabs: 2,
      bars: 5,
      nightclubs: 1,
      adult_shops: 0,
      tabac: 2
    }
  };