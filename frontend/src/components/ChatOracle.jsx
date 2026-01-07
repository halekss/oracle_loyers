import { useState, useEffect, useRef } from 'react';

export default function ChatOracle() {
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [messages, setMessages] = useState([
    { 
      id: 1, 
      sender: 'oracle', 
      text: "Je vois tout. Pose-moi une question sur ce quartier, si tu oses." 
    }
  ]);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // --- LOGIQUE DE SIMULATION ---
  const getCynicalResponse = (userText) => {
    const lowerText = userText.toLowerCase();
    
    if (lowerText.includes('calme') || lowerText.includes('bruit')) 
      return "Le calme ? C'est un concept abstrait ici. Entre les klaxons et les étudiants en art dramatique, prévois du double vitrage.";
    
    if (lowerText.includes('sécurité') || lowerText.includes('dangereux')) 
      return "Disons que courir vite est une compétence valorisée dans ce secteur après 23h.";
    
    if (lowerText.includes('prix') || lowerText.includes('cher')) 
      return "C'est hors de prix pour ce que c'est. Tu paies la 'vibe', pas les m².";
    
    if (lowerText.includes('kebab') || lowerText.includes('manger')) 
      return "L'offre gastronomique se résume à de la friture et des doutes sanitaires.";

    return "Les astres sont flous... mais mon algorithme me dit que tu vas regretter cet investissement.";
  };

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    // 1. User Message
    const userMsg = { id: Date.now(), sender: 'user', text: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    // 2. Oracle Response
    setTimeout(() => {
      const replyText = getCynicalResponse(userMsg.text);
      const oracleMsg = { id: Date.now() + 1, sender: 'oracle', text: replyText };
      
      setMessages(prev => [...prev, oracleMsg]);
      setIsTyping(false);
    }, 1500); 
  };

  return (
    // ICI : w-full h-full pour remplir le parent de App.jsx
    <div className="w-full h-full flex flex-col bg-transparent">
      
      {/* HEADER DU CHAT */}
      <div className="bg-slate-950/50 p-3 border-b border-purple-500/20 flex items-center gap-3 shrink-0">
        <div className="w-2 h-2 bg-green-500 rounded-full shadow-[0_0_10px_#22c55e] animate-pulse"></div>
        <h3 className="text-purple-300 font-mono text-xs tracking-widest uppercase font-bold">
          Oracle_Live_Link_v2.0
        </h3>
      </div>

      {/* ZONE DE MESSAGES (flex-1 pour prendre la place dispo) */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-purple-900 scrollbar-track-transparent">
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div 
              className={`max-w-[85%] p-3 rounded-2xl text-sm leading-relaxed ${
                msg.sender === 'user' 
                  ? 'bg-purple-600 text-white rounded-tr-none shadow-lg' 
                  : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-none'
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}
        
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-slate-800 p-3 rounded-2xl rounded-tl-none border border-slate-700 flex gap-1">
              <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce"></span>
              <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce delay-75"></span>
              <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce delay-150"></span>
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
          placeholder="Posez une question..."
          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all"
        />
        <button 
          type="submit"
          disabled={!input.trim() || isTyping}
          className="bg-purple-600 hover:bg-purple-500 text-white px-4 rounded-lg font-bold transition-colors disabled:opacity-50"
        >
          ➤
        </button>
      </form>
    </div>
  );
}