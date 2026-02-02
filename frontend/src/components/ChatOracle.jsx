import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatOracle({ analysis, context, quartier }) {
  // Message d'accueil par défaut
  const [messages, setMessages] = useState([
    { 
      sender: 'oracle', 
      text: "🔮 **L'Oracle t'écoute.** Tape une adresse pour lancer un scan, ou pose-moi une question sur le quartier." 
    }
  ]);
  
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // 1. Quand une nouvelle analyse arrive (depuis le scan), l'Oracle parle tout seul
  useEffect(() => {
    if (analysis) {
      setMessages(prev => [...prev, { sender: 'oracle', text: analysis }]);
    }
  }, [analysis]);

  // 2. Scroll automatique vers le bas à chaque nouveau message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 3. Envoi du message utilisateur
  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    
    // Affiche le message de l'utilisateur tout de suite
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setInput('');
    setIsLoading(true);

    try {
      // Envoie le message + le contexte (prix, quartier...) au Backend
      const oracleResponse = await api.sendChatMessage(userMsg, context);
      
      // Affiche la réponse de l'Oracle
      setMessages(prev => [...prev, { sender: 'oracle', text: oracleResponse }]);
    } catch (error) {
      console.error('❌ Erreur chat:', error);
      setMessages(prev => [...prev, { 
        sender: 'oracle', 
        text: "⚠️ **Erreur de connexion.** L'Oracle est en pause café (vérifie ton terminal backend)." 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-slate-950/50">
      
      {/* --- ZONE DE MESSAGES (Scrollable) --- */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5 custom-scrollbar">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex w-full ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            
            <div 
              className={`max-w-[90%] md:max-w-[85%] px-5 py-3 rounded-2xl text-sm leading-relaxed shadow-md backdrop-blur-sm ${
                msg.sender === 'user' 
                  ? 'bg-purple-600 text-white rounded-br-sm' 
                  : 'bg-slate-800 text-slate-200 border border-slate-700/50 rounded-bl-sm'
              }`}
            >
              {msg.sender === 'oracle' ? (
                // Rendu Markdown pour l'Oracle (Gras, Titres, Listes...)
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    // Correction : on ne récupère pas 'node' pour éviter le warning console
                    strong: (props) => <span className="font-bold text-yellow-400" {...props} />,
                    h3: (props) => <h3 className="text-xs font-black uppercase tracking-widest text-purple-300 mb-2 mt-4 border-b border-slate-600 pb-1" {...props} />,
                    ul: (props) => <ul className="list-disc pl-4 space-y-1 my-2" {...props} />,
                    li: (props) => <li className="marker:text-purple-500 pl-1" {...props} />,
                    p: (props) => <p className="mb-2 last:mb-0" {...props} />,
                    a: (props) => <a className="text-blue-400 underline" {...props} />
                  }}
                >
                  {msg.text}
                </ReactMarkdown>
              ) : (
                // Texte simple pour l'utilisateur
                <p>{msg.text}</p>
              )}
            </div>
          </div>
        ))}
        
        {/* Bulle de chargement animée */}
        {isLoading && (
          <div className="flex justify-start w-full animate-pulse">
            <div className="bg-slate-800/50 border border-slate-700 rounded-2xl rounded-bl-sm px-4 py-3">
              <div className="flex gap-1.5">
                <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce delay-75"></div>
                <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce delay-150"></div>
              </div>
            </div>
          </div>
        )}
        
        {/* Élément invisible pour scroller en bas automatiquement */}
        <div ref={messagesEndRef} />
      </div>

      {/* --- ZONE DE SAISIE (Input) --- */}
      <div className="p-3 bg-slate-900 border-t border-slate-800">
        
        {/* Indicateur de Contexte (Si un scan est actif) */}
        {context && (
          <div className="flex items-center gap-2 mb-2 px-2 opacity-70">
            <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
              Contexte : {quartier || 'Zone active'}
            </span>
          </div>
        )}

        <form onSubmit={handleSend} className="relative flex items-center gap-2">
          <input
            type="text"
            className="flex-1 bg-slate-950 border border-slate-700 hover:border-slate-600 text-slate-100 text-sm px-4 py-3 rounded-xl focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder:text-slate-600"
            placeholder="Pose ta question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          <button 
            type="submit"
            disabled={isLoading || !input.trim()}
            className="p-3 bg-purple-600 hover:bg-purple-500 active:bg-purple-700 rounded-xl text-white transition-all shadow-lg shadow-purple-900/20 disabled:opacity-50 disabled:cursor-not-allowed transform active:scale-95"
          >
            {/* Icône Envoyer */}
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
              <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}