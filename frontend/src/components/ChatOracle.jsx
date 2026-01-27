import { useState, useEffect, useRef } from 'react';

// On accepte la prop 'analysis' qui vient de App.jsx
export default function ChatOracle({ analysis }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { 
      id: 1, 
      sender: 'oracle', 
      text: "Je vois tout. Pose-moi une question sur ce quartier, si tu oses." 
    }
  ]);
  const messagesEndRef = useRef(null);

  // --- 1. ECOUTE DE L'ANALYSE BACKEND ---
  // Dès que 'analysis' change (quand on reçoit une réponse du Python), on l'ajoute au chat
  useEffect(() => {
    if (analysis && analysis.length > 0) {
      // On transforme les textes bruts du Python en objets messages
      const newMessages = analysis.map((text, index) => ({
        id: Date.now() + index, // ID unique
        sender: 'oracle',
        text: text
      }));
      
      // On ajoute ces messages à la suite des autres
      setMessages(prev => [...prev, ...newMessages]);
    }
  }, [analysis]); // <--- C'est ici que la magie opère

  // Scroll automatique vers le bas
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Ajout message utilisateur
    const userMsg = { id: Date.now(), sender: 'user', text: input };
    setMessages(prev => [...prev, userMsg]);
    
    // Réponse générique (si pas d'appel backend) pour garder le chat vivant
    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'oracle',
        text: "Intéressant... mais regarde plutôt les données que je t'ai trouvées à gauche."
      }]);
    }, 1000);

    setInput('');
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50">
      {/* ZONE DES MESSAGES */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`
              max-w-[80%] p-3 rounded-2xl text-sm leading-relaxed shadow-lg
              ${msg.sender === 'user' 
                ? 'bg-blue-600 text-white rounded-tr-none' 
                : 'bg-slate-800 text-slate-200 border border-purple-500/30 rounded-tl-none'}
            `}>
              {/* Si c'est l'oracle, on met une petite icône */}
              {msg.sender === 'oracle' && <span className="mr-2">🔮</span>}
              {msg.text}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* BARRE DE SAISIE */}
      <form onSubmit={handleSend} className="p-3 bg-slate-950/30 border-t border-purple-500/20 flex gap-2 shrink-0">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Répondre à l'Oracle..."
          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500 transition-colors"
        />
        <button 
          type="submit"
          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          ➤
        </button>
      </form>
    </div>
  );
}