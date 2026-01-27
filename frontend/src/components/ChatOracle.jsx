import { useState, useEffect, useRef } from 'react';

export default function ChatOracle({ analysis }) {
  const [input, setInput] = useState('');
  // 1. VOICI LA VARIABLE QUI MANQUAIT :
  const [isTyping, setIsTyping] = useState(false);
  
  const [messages, setMessages] = useState([
    { 
      id: 1, 
      sender: 'oracle', 
      text: "Je vois tout. Pose-moi une question sur ce quartier, si tu oses." 
    }
  ]);
  const messagesEndRef = useRef(null);

  // --- 2. ECOUTE DU BACKEND (Quand l'IA répond après une recherche) ---
  useEffect(() => {
    if (analysis && analysis.length > 0) {
      setIsTyping(true); // On fait semblant de réfléchir un peu
      
      setTimeout(() => {
        setIsTyping(false);
        const newMessages = analysis.map((text, index) => ({
          id: Date.now() + index,
          sender: 'oracle',
          text: text
        }));
        setMessages(prev => [...prev, ...newMessages]);
      }, 1500); // Délai dramatique de 1.5s
    }
  }, [analysis]);

  // Scroll automatique
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Message utilisateur
    const userMsg = { id: Date.now(), sender: 'user', text: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    
    // Réponse automatique (Simulation si pas d'analyse en cours)
    setIsTyping(true);
    setTimeout(() => {
      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'oracle',
        text: "Intéressant... mais concentre-toi plutôt sur les données à gauche, c'est là que se trouve la vérité."
      }]);
    }, 1000);
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
              max-w-[80%] p-3 rounded-2xl text-sm leading-relaxed shadow-lg animate-fade-in-up
              ${msg.sender === 'user' 
                ? 'bg-blue-600 text-white rounded-tr-none' 
                : 'bg-slate-800 text-slate-200 border border-purple-500/30 rounded-tl-none'}
            `}>
              {msg.sender === 'oracle' && <span className="mr-2">🔮</span>}
              {msg.text}
            </div>
          </div>
        ))}

        {/* 3. L'ANIMATION DE FRAPPE (C'est elle qui plantait) */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-slate-800 p-3 rounded-2xl rounded-tl-none border border-slate-700 flex gap-1">
              <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce"></span>
              <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce delay-75"></span>
              <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce delay-150"></span>
            </div>
          </div>
        )}
        
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
          disabled={isTyping}
          className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg transition-colors"
        >
          ➤
        </button>
      </form>
    </div>
  );
}