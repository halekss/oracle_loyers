import React, { useState, useEffect, useRef } from 'react';

export default function ChatOracle({ analysis }) {
  const [messages, setMessages] = useState([
    { sender: 'oracle', text: "Initialisation... Sélectionnez une zone sur la carte ou entrez une adresse pour commencer l'analyse." }
  ]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  // Mise à jour quand une nouvelle analyse arrive
  useEffect(() => {
    if (analysis) {
      setMessages(prev => [...prev, { sender: 'oracle', text: analysis }]);
    }
  }, [analysis]);

  // Scroll automatique vers le bas
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    const userMsg = { sender: 'user', text: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    
    // Simulation réponse (à connecter à une API plus tard)
    setTimeout(() => {
        setMessages(prev => [...prev, { sender: 'oracle', text: "Je n'ai pas encore accès à la fonction chat temps réel, mais j'analyse les données géographiques." }]);
    }, 1000);
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
                  ? 'bg-purple-600 text-white rounded-br-none' 
                  : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-bl-none'
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* ZONE DE SAISIE (Fixe en bas) */}
      <div className="p-4 bg-slate-900 border-t border-slate-800">
        <form onSubmit={handleSend} className="flex gap-2">
          <input
            type="text"
            className="flex-1 bg-slate-950 border border-slate-700 text-slate-200 text-xs px-4 py-3 rounded-full focus:outline-none focus:border-purple-500 transition-colors"
            placeholder="Poser une question à l'Oracle..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button 
            type="submit"
            className="p-3 bg-purple-600 hover:bg-purple-500 rounded-full text-white transition-colors shadow-lg shadow-purple-900/50"
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