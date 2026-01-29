import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';

export default function ChatOracle({ analysis, mlContext }) {
  const [messages, setMessages] = useState([
    { 
      sender: 'oracle', 
      text: "🔮 Bienvenue, mortel. Je suis l'Oracle de Lyon.\n\nPour commencer :\n1. Clique sur la carte pour scanner une zone\n2. OU tape une adresse (ex: 'Croix-Rousse')\n\nEnsuite, pose-moi tes questions sur les loyers."
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasActiveContext, setHasActiveContext] = useState(false);
  const messagesEndRef = useRef(null);
  const lastContextTimestamp = useRef(null);

  // 🔥 DÉTECTION D'UN NOUVEAU SCAN ML
  useEffect(() => {
    if (mlContext && mlContext.ml_ready && mlContext.timestamp !== lastContextTimestamp.current) {
      lastContextTimestamp.current = mlContext.timestamp;
      setHasActiveContext(true);
      
      // Message automatique de l'Oracle après un scan
      const autoMessage = `✅ **Scan terminé !**

📍 Zone : ${mlContext.zone}
💰 Loyer estimé : ${mlContext.prix_estime}€ (${mlContext.prix_m2}€/m²)
🏠 Type : ${mlContext.type_estime}

💡 Pose-moi une question :
• "analyse" → verdict détaillé
• "c'est cher ?" → comparaison rapide
• "pourquoi ce prix ?" → facteurs clés`;
      
      setMessages(prev => [...prev, { sender: 'oracle', text: autoMessage }]);
    }
  }, [mlContext?.timestamp]);

  // Auto-scroll vers le bas
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setInput('');
    setIsLoading(true);

    try {
      // 🔥 ENVOI DU CONTEXTE ML STRUCTURÉ
      const contextToSend = hasActiveContext && mlContext ? {
        ml_ready: true,
        prix_estime: mlContext.prix_estime,
        prix_m2: mlContext.prix_m2,
        zone: mlContext.zone,
        type_estime: mlContext.type_estime,
        confiance: mlContext.confiance || 85,
        arrondissement: mlContext.arrondissement || "N/A",
        prix_median_zone: mlContext.prix_median_zone,
        ecart_median: mlContext.ecart_median,
        ecart_euros: mlContext.ecart_euros || 0,
        tendance: mlContext.tendance,
        metro_proche: mlContext.metro_proche || "N/A",
        distance_metro: mlContext.distance_metro || "N/A",
        nb_vice: mlContext.nb_vice || 0,
        nb_gentri: mlContext.nb_gentri || 0,
        nb_nuisance: mlContext.nb_nuisance || 0,
        facteurs_cles: mlContext.facteurs_cles || []
      } : null;

      console.log("📤 Envoi au chatbot :", {
        message: userMsg,
        hasContext: !!contextToSend
      });

      const oracleResponse = await api.sendChatMessage(userMsg, contextToSend);
      
      setMessages(prev => [...prev, { 
        sender: 'oracle', 
        text: oracleResponse 
      }]);
    } catch (error) {
      console.error('❌ Erreur chat:', error);
      
      let errorMsg = "⚠️ Une erreur s'est produite.";
      
      if (error.message.includes('503') || error.message.includes('1234')) {
        errorMsg = `❌ **Impossible de joindre LM Studio**

Vérifications :
1. LM Studio est-il lancé ?
2. Un modèle est-il chargé ?
3. Le serveur écoute-t-il sur http://localhost:1234 ?

Une fois corrigé, réessaye ta question.`;
      }
      
      setMessages(prev => [...prev, { 
        sender: 'oracle', 
        text: errorMsg
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // 🔥 BOUTON RAPIDE "Analyse ce scan"
  const handleQuickAnalyze = () => {
    if (!mlContext || isLoading) return;
    
    // Simule un clic sur le bouton d'envoi avec le message "analyse"
    const analyzeBtn = document.querySelector('button[data-analyze]');
    if (analyzeBtn) {
      setInput("analyse");
      setTimeout(() => {
        document.querySelector('button[type="submit"]')?.click();
      }, 100);
    }
  };

  // 🔥 BOUTONS SUGGÉRÉS
  const quickQuestions = [
    { label: "C'est cher ?", question: "c'est cher ?" },
    { label: "Pourquoi ce prix ?", question: "pourquoi ce prix ?" },
    { label: "Analyse complète", question: "analyse" }
  ];

  const handleQuickQuestion = (question) => {
    if (isLoading) return;
    setInput(question);
    setTimeout(() => {
      document.querySelector('button[type="submit"]')?.click();
    }, 100);
  };

  return (
    <div className="flex flex-col h-full w-full bg-slate-950">
      
      {/* ZONE DE MESSAGES (Scrollable) */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div 
              className={`max-w-[85%] p-3 rounded-2xl text-xs leading-relaxed whitespace-pre-line ${
                msg.sender === 'user' 
                  ? 'bg-purple-600 text-white rounded-br-none shadow-lg' 
                  : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-bl-none'
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}
        
        {/* Indicateur de chargement */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 text-slate-400 border border-slate-700 rounded-2xl rounded-bl-none p-3 text-xs">
              <span className="inline-flex gap-1">
                <span className="animate-bounce">●</span>
                <span className="animate-bounce delay-100">●</span>
                <span className="animate-bounce delay-200">●</span>
              </span>
              <span className="ml-2">L'Oracle consulte les arcanes...</span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 🔥 BOUTONS RAPIDES (Visible seulement si scan ML actif) */}
      {mlContext && mlContext.ml_ready && !isLoading && (
        <div className="px-4 pb-2 space-y-2">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
            Questions suggérées :
          </p>
          <div className="flex gap-2">
            {quickQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleQuickQuestion(q.question)}
                className="flex-1 py-2 bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 rounded-lg text-purple-300 text-[11px] font-medium transition-all hover:scale-105"
              >
                {q.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ZONE DE SAISIE (Fixe en bas) */}
      <div className="p-4 bg-slate-900 border-t border-slate-800">
        <form onSubmit={handleSend} className="flex gap-2">
          <input
            type="text"
            className="flex-1 bg-slate-950 border border-slate-700 text-slate-200 text-xs px-4 py-3 rounded-full focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            placeholder={
              hasActiveContext 
                ? "Pose ta question (ex: 'c'est cher ?')..." 
                : "Lance un scan d'abord en cliquant sur la carte..."
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          <button 
            type="submit"
            disabled={isLoading || !input.trim()}
            className="p-3 bg-purple-600 hover:bg-purple-500 rounded-full text-white transition-all shadow-lg shadow-purple-900/50 disabled:opacity-50 disabled:cursor-not-allowed hover:scale-110 active:scale-95"
            title="Envoyer"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </form>
        
        {/* Indicateur d'état */}
        <div className="mt-2 text-center">
          {isLoading ? (
            <p className="text-xs text-purple-400">
              Analyse en cours{mlContext ? ` (${mlContext.zone})` : ''}...
            </p>
          ) : hasActiveContext ? (
            <p className="text-xs text-green-400">
              ✓ Scan actif : {mlContext.zone} ({mlContext.prix_estime}€)
            </p>
          ) : (
            <p className="text-xs text-slate-500">
              Aucun scan actif
            </p>
          )}
        </div>
      </div>

      {/* Style custom pour la scrollbar */}
      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgb(15 23 42);
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgb(71 85 105);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgb(100 116 139);
        }
      `}</style>
    </div>
  );
}