import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api'; // On importe l'API

export default function ChatOracle({ analysis }) {
  // Message de bienvenue par défaut
  const [messages, setMessages] = useState([
    { sender: 'oracle', text: "Initialisation... Sélectionnez une zone sur la carte ou entrez une adresse pour commencer l'analyse." }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false); // Pour l'effet "L'Oracle écrit..."
  const messagesEndRef = useRef(null);

  // 1. Quand une nouvelle analyse arrive (depuis le SCAN), l'Oracle parle en premier
  useEffect(() => {
    if (analysis) {
      setMessages(prev => [...prev, { sender: 'oracle', text: analysis }]);
    }
  }, [analysis]);

  // Scroll automatique vers le bas
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // 2. Gestion de l'envoi de message
  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userText = input;
    
    // A. On affiche le message de l'utilisateur tout de suite
    setMessages(prev => [...prev, { sender: 'user', text: userText }]);
    setInput('');
    setIsTyping(true); // On montre que ça charge

    try {
        // B. APPEL À LA VRAIE API (Backend -> LM Studio)
        const data = await api.getChatResponse(userText);
        
        // C. On affiche la réponse de l'IA
        setMessages(prev => [...prev, { sender: 'oracle', text: data.response }]);
    } catch (error) {
        setMessages(prev => [...prev, { sender: 'oracle', text: "Mes visions sont brouillées (Erreur de connexion)." }]);
    } finally {
        setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-slate-950 border-t border-slate-800">
      
      {/* ZONE DE MESSAGES */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div 
              className={`max-w-[85%] p-3 rounded-2xl text-xs leading-relaxed shadow-md ${
                msg.sender === 'user' 
                  ? 'bg-purple-600 text-white rounded-br-none' 
                  : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-bl-none'
              }`}
            >
              {/* On rend le texte de l'IA un peu plus lisible s'il y a du gras/markdown */}
              {msg.text}
            </div>
          </div>
        ))}
        
        {/* Indicateur de frappe */}
        {isTyping && (
           <div className="flex justify-start">
             <div className="bg-slate-800 p-3 rounded-2xl rounded-bl-none border border-slate-700 flex gap-1">
                <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce"></span>
                <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce delay-100"></span>
                <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce delay-200"></span>
             </div>
           </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* ZONE DE SAISIE */}
      <div className="p-4 bg-slate-900 border-t border-slate-800">
        <form onSubmit={handleSend} className="flex gap-2">
          <input
            type="text"
            className="flex-1 bg-slate-950 border border-slate-700 text-slate-200 text-xs px-4 py-3 rounded-full focus:outline-none focus:border-purple-500 transition-colors"
            placeholder="Poser une question à l'Oracle..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isTyping}
          />
          <button 
            type="submit"
            disabled={isTyping}
            className="p-3 bg-purple-600 hover:bg-purple-500 rounded-full text-white transition-colors shadow-lg shadow-purple-900/50 disabled:opacity-50"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}