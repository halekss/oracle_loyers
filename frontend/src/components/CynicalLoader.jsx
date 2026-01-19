import { useState, useEffect } from 'react';

const MESSAGES = [
  "Espionnage des voisins...",
  "Analyse de la qualité du kebab le plus proche...",
  "Calcul du risque de tapage nocturne...",
  "Vérification de la présence de punaises de lit...",
  "Mesure de la distance avec le premier dealer...",
  "Inspection des poubelles du quartier...",
  "Consultation des esprits immobiliers...",
  "Recherche des vices cachés...",
  "Tri sélectif des préjugés..."
];

export default function CynicalLoader() {
  const [currentMessage, setCurrentMessage] = useState(MESSAGES[0]);

  useEffect(() => {
    // Change la phrase toutes les 800ms
    const interval = setInterval(() => {
      const randomIndex = Math.floor(Math.random() * MESSAGES.length);
      setCurrentMessage(MESSAGES[randomIndex]);
    }, 800);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center mt-8 space-y-4">
      {/* Animation du rond qui tourne (Spinner) */}
      <div className="relative w-16 h-16">
        <div className="absolute top-0 left-0 w-full h-full border-4 border-slate-700 rounded-full"></div>
        <div className="absolute top-0 left-0 w-full h-full border-4 border-purple-500 rounded-full border-t-transparent animate-spin"></div>
      </div>
      
      {/* Le texte cynique qui change */}
      <p className="text-purple-300 font-mono text-sm md:text-base animate-pulse text-center px-4">
        {currentMessage}
      </p>
    </div>
  );
}