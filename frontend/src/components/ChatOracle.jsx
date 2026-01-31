import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';

export default function ChatOracle({ analysis, context, quartier }) {
  const [messages, setMessages] = useState([
    { 
      sender: 'oracle', 
      text: "🔮 Bienvenue, mortel. Tape une adresse dans la barre de recherche (ex: 'Ainay'), puis pose-moi tes questions..." 
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Mise à jour quand une nouvelle analyse arrive
  useEffect(() => {
    if (analysis) {
      setMessages(prev => [...prev, { sender: 'oracle', text: analysis }]);
    }
  }, [analysis]);

  // Auto-scroll vers le bas
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    
    // Ajouter le message utilisateur
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setInput('');
    setIsLoading(true);

    try {
      // 🎯 APPEL API AVEC LE CONTEXTE AUTOMATIQUE
      const oracleResponse = await api.sendChatMessage(userMsg, context);
      
      // Ajouter la réponse de l'Oracle
      setMessages(prev => [...prev, { 
        sender: 'oracle', 
        text: oracleResponse 
      }]);
    } catch (error) {
      console.error('❌ Erreur chat:', error);
      setMessages(prev => [...prev, { 
        sender: 'oracle', 
        text: "⚠️ Une erreur s'est produite. Vérifie que LM Studio tourne sur le port 1234." 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-slate-950 border-t border-slate-800">
      
      {/* ZONE DE MESSAGES (Scrollable) */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div 
              className={`max-w-[85%] p-3 rounded-2xl text-xs leading-relaxed ${
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
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* ZONE DE SAISIE (Fixe en bas) */}
      <div className="p-4 bg-slate-900 border-t border-slate-800">
        <form onSubmit={handleSend} className="flex gap-2">
          <input
            type="text"
            className="flex-1 bg-slate-950 border border-slate-700 text-slate-200 text-xs px-4 py-3 rounded-full focus:outline-none focus:border-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            placeholder="Interroge l'Oracle (ex: 'C'est cher ?')..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          <button 
            type="submit"
            disabled={isLoading || !input.trim()}
            className="p-3 bg-purple-600 hover:bg-purple-500 rounded-full text-white transition-colors shadow-lg shadow-purple-900/50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </form>
        
        {/* Indicateur de contexte actif */}
        {context && (
          <p className="text-xs text-purple-400 mt-2 text-center">
            💡 Scan actif : {quartier || 'Zone détectée'}
          </p>
        )}
        
        {isLoading && (
          <p className="text-xs text-slate-500 mt-2 text-center">
            L'Oracle consulte les arcanes...
          </p>
        )}
      </div>
    </div>
  );
}