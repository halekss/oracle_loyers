import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatOracle({ analysis, context, quartier, onInsight }) {
  // Message d'accueil par défaut
  const [messages, setMessages] = useState([
    { 
      sender: 'oracle', 
      text: "**Immotep est en ligne.** Pose une question sur un quartier, un prix ou une surface; il répondra sans vendre du rêve au mètre carré."
    }
  ]);
  
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [latestInsight, setLatestInsight] = useState(null);
  const messagesEndRef = useRef(null);

  // 1. Quand une nouvelle analyse arrive (depuis le scan), Immotep parle tout seul
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
      const oracleResponse = await api.sendChatMessage(userMsg, buildChatContext(context, latestInsight));
      const responseText = typeof oracleResponse === 'string' ? oracleResponse : oracleResponse.response;
      
      // Affiche la réponse d'Immotep
      setMessages(prev => [...prev, { sender: 'oracle', text: responseText }]);
      if (typeof oracleResponse === 'object') {
        setLatestInsight(oracleResponse);
        onInsight?.(oracleResponse);
      }
    } catch (error) {
      console.error('Erreur chat:', error);
      setMessages(prev => [...prev, { 
        sender: 'oracle', 
        text: "**Service indisponible.** Immotep est en pause café. Réessaie dans quelques instants."
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
              className={`max-w-[88%] md:max-w-[82%] px-4 py-3 rounded-xl text-sm leading-relaxed shadow-md backdrop-blur-sm ${
                msg.sender === 'user' 
                  ? 'bg-indigo-600 text-white rounded-br-sm' 
                  : 'bg-slate-800 text-slate-200 border border-slate-700/60 rounded-bl-sm'
              }`}
            >
              {msg.sender === 'oracle' ? (
                // Rendu Markdown pour Immotep (Gras, Titres, Listes...)
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    // Correction : on ne récupère pas 'node' pour éviter le warning console
                    strong: (props) => <span className="font-bold text-amber-300" {...props} />,
                    h3: (props) => <h3 className="text-xs font-black uppercase tracking-widest text-cyan-300 mb-2 mt-4 border-b border-slate-600 pb-1" {...props} />,
                    ul: (props) => <ul className="list-disc pl-4 space-y-1 my-2" {...props} />,
                    li: (props) => <li className="marker:text-cyan-400 pl-1" {...props} />,
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
          <div className="flex justify-start w-full">
            <div className="bg-slate-800/70 border border-slate-700 rounded-xl rounded-bl-sm px-4 py-3 text-sm text-slate-300">
              <div className="flex items-center gap-3">
                <span>Analyse en cours</span>
                <div className="flex gap-1.5" aria-hidden="true">
                  <div className="w-1.5 h-1.5 bg-cyan-300 rounded-full animate-bounce"></div>
                  <div className="w-1.5 h-1.5 bg-cyan-300 rounded-full animate-bounce delay-75"></div>
                  <div className="w-1.5 h-1.5 bg-cyan-300 rounded-full animate-bounce delay-150"></div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Élément invisible pour scroller en bas automatiquement */}
        <div ref={messagesEndRef} />
      </div>

      {/* --- ZONE DE SAISIE (Input) --- */}
      <div className="p-3 bg-slate-900 border-t border-slate-800">
        {latestInsight && (
          <InsightPanel insight={latestInsight} />
        )}
        
        {/* Indicateur de Contexte (Si un scan est actif) */}
        {context && (
          <div className="flex items-center gap-2 mb-2 px-2 opacity-70">
            <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
              Secteur actif : {quartier || 'zone scannée'}
            </span>
          </div>
        )}

        <form onSubmit={handleSend} className="relative flex items-center gap-2">
          <input
            type="text"
            className="flex-1 bg-slate-950 border border-slate-700 hover:border-slate-600 text-slate-100 text-sm px-4 py-3 rounded-lg focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all placeholder:text-slate-600"
            placeholder="Prix, surface, quartier..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          <button 
            type="submit"
            disabled={isLoading || !input.trim()}
            className="p-3 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 rounded-lg text-white transition-all shadow-lg shadow-indigo-900/20 disabled:opacity-50 disabled:cursor-not-allowed transform active:scale-95"
            aria-label="Envoyer le message"
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

function buildChatContext(baseContext, insight) {
  const parts = [];
  if (baseContext) parts.push(baseContext);

  const parsed = insight?.parsed;
  if (parsed) {
    if (parsed.locations?.length) {
      parts.push(`Conversation précédente: ${parsed.locations.join(', ')}`);
    }
    if (parsed.postal_code) {
      parts.push(`Code postal: ${parsed.postal_code}`);
    }
    if (parsed.preferences?.length) {
      parts.push(`Préférences: ${parsed.preferences.join(', ')}`);
    }
    if (parsed.type_locals?.length) {
      parts.push(`Types: ${parsed.type_locals.join(', ')}`);
    } else if (parsed.type_local) {
      parts.push(`Type: ${parsed.type_local}`);
    }
  }

  return parts.join('. ');
}

function InsightPanel({ insight }) {
  const [isOpen, setIsOpen] = useState(true);
  const comparisons = insight.comparisons || [];
  const recommendations = insight.recommendations || [];
  const hasComparisons = comparisons.length > 0;
  const items = hasComparisons ? comparisons : recommendations;

  if (!items.length) return null;

  return (
    <div className="mb-3 border border-slate-700/70 bg-slate-950/70 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen((value) => !value)}
        className="w-full px-3 py-2 border-b border-slate-800 flex items-center justify-between text-left hover:bg-slate-900/70 transition-colors"
        aria-expanded={isOpen}
      >
        <span className="flex items-center gap-2 min-w-0">
          <span className="text-[10px] uppercase tracking-widest text-cyan-300 font-bold">
            {hasComparisons ? 'Comparaison Immotep' : 'Suggestions Immotep'}
          </span>
          {insight.map_focus?.quartier && (
            <span className="text-[10px] text-slate-500 truncate">
              Focus: {insight.map_focus.quartier}
            </span>
          )}
        </span>
        <span className="text-slate-500 text-xs font-mono">
          {isOpen ? '−' : '+'}
        </span>
      </button>

      {isOpen && (
        <div className="divide-y divide-slate-800 max-h-48 overflow-y-auto">
          {items.slice(0, 4).map((item, index) => (
            <div key={`${item.quartier}-${index}`} className="px-3 py-2 text-xs">
              <div className="flex items-center justify-between gap-3">
                <span className="font-semibold text-slate-100 truncate">
                  {item.quartier}
                </span>
                <span className="font-mono text-amber-300 whitespace-nowrap">
                  {Math.round(item.prix_moyen ?? item.prix ?? 0).toLocaleString('fr-FR')} €
                </span>
              </div>
              <div className="mt-1 text-slate-400 flex flex-wrap gap-x-3 gap-y-1">
                {item.type_local && <span>{item.type_local}</span>}
                {item.surface && <span>{item.surface} m²</span>}
                {item.surface_moyenne && <span>{item.surface_moyenne} m² moy.</span>}
                {item.prix_m2_moyen && <span>{item.prix_m2_moyen} €/m²</span>}
                {item.count && <span>{item.count} annonces</span>}
              </div>
              {item.why && (
                <p className="mt-1 text-slate-500 leading-snug">{item.why}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
