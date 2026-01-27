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

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userText = input.trim();
    // 1. Ajouter le message utilisateur à l'écran
    const userMsg = { id: Date.now(), sender: 'user', text: userText };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    // Créer un AbortController avec timeout de 2 minutes
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 secondes

    try {
      // 2. Appel au backend FastAPI (Docker)
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userText }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Erreur ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // 3. Ajouter la réponse de l'Oracle (LM Studio via Backend)
      const oracleMsg = { 
        id: Date.now() + 1, 
        sender: 'oracle', 
        text: data.response 
      };
      setMessages(prev => [...prev, oracleMsg]);

    } catch (error) {
      clearTimeout(timeoutId);
      console.error('Erreur complète:', error);
      
      // Message d'erreur adapté selon le type d'erreur
      let errorMessage = "ERREUR : Ma matrice de réflexion est instable.";
      
      if (error.name === 'AbortError') {
        errorMessage = "⏳ L'Oracle médite profondément... Ça prend plus de 2 minutes. Réessaye avec une question plus courte ou patiente encore.";
      } else if (error.message.includes('Failed to fetch')) {
        errorMessage = "🔌 Impossible de contacter le backend. Vérifie que Docker tourne sur le port 8000.";
      } else if (error.message.includes('500')) {
        errorMessage = "⚠️ Le backend a rencontré une erreur. Vérifie les logs Docker et que LM Studio est bien démarré.";
      } else {
        errorMessage = `ERREUR : ${error.message}`;
      }
      
      const errorMsg = { 
        id: Date.now() + 1, 
        sender: 'oracle', 
        text: errorMessage
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-transparent">
      
      {/* HEADER DU CHAT */}
      <div className="bg-slate-950/50 p-3 border-b border-purple-500/20 flex items-center gap-3 shrink-0">
        <div className="w-2 h-2 bg-green-500 rounded-full shadow-[0_0_10px_#22c55e] animate-pulse"></div>
        <h3 className="text-purple-300 font-mono text-xs tracking-widest uppercase font-bold">
          Oracle_Live_Link_v2.0
        </h3>
      </div>

      {/* ZONE DE MESSAGES */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-purple-900 scrollbar-track-transparent">
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
<<<<<<< HEAD
          placeholder="Répondre à l'Oracle..."
          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500 transition-colors"
        />
        <button 
          type="submit"
          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
=======
          placeholder="Posez une question à l'Oracle..."
          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all"
          disabled={isTyping}
        />
        <button 
          type="submit"
          disabled={!input.trim() || isTyping}
          className="bg-purple-600 hover:bg-purple-500 text-white px-4 rounded-lg font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
>>>>>>> main
        >
          {isTyping ? '⏳' : '➤'}
        </button>
      </form>
    </div>
  );
}