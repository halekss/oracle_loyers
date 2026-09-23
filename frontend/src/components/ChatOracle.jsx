import React, { useState, useEffect, useRef } from 'react';
import { api, ApiError } from '../services/api';
import { loadChatHistory, saveChatHistory } from '../services/chatHistoryStorage';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const describeChatError = (error) => {
  if (error instanceof ApiError) {
    switch (error.type) {
      case 'network':
        return "**Connexion perdue.** Immotep ne capte plus de réseau, vérifie ta connexion et réessaie.";
      case 'rate_limit':
        return "**Doucement.** Immotep a une limite de questions par heure pour économiser son quota. Reviens dans un instant.";
      case 'client':
        return "**Requête refusée.** Immotep n'a pas compris la demande envoyée.";
      case 'server':
        return "**Service indisponible.** Le serveur d'Immotep tousse, réessaie dans quelques instants.";
      default:
        break;
    }
  }
  return "**Service indisponible.** Immotep est en pause café. Réessaie dans quelques instants.";
};

const DEFAULT_MESSAGES = [
  {
    sender: 'oracle',
    text: "**Immotep est en ligne.** Pose une question sur un quartier, un prix ou une surface; il répondra sans vendre du rêve au mètre carré."
  }
];

// ORA-175 : types de bien connus, pour générer une suggestion "Et en T3 ?"
// après une réponse qui portait sur un autre type précis.
const ALL_TYPES = ['T1', 'T2', 'T3', 'T4+'];

// `onListAnnonces` (optionnel, ORA-175) : appelé avec le quartier dominant
// des recommandations quand l'utilisateur clique "Lister les N annonces" —
// le parent (App.jsx) bascule vers la liste des annonces sur ce quartier.
// Filtrer la liste par type/budget précis dépasse le périmètre de ce ticket
// (AnnoncesList n'accepte aujourd'hui qu'un filtre quartier, cf. ORA-115).
export default function ChatOracle({ analysis, context, quartier, onInsight, onListAnnonces }) {
  // ORA-117 : restaure l'historique de la session (sessionStorage) au
  // montage — vide dans un nouvel onglet, conservé au refresh de page.
  const [messages, setMessages] = useState(() => loadChatHistory() || DEFAULT_MESSAGES);

  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [latestInsight, setLatestInsight] = useState(null);
  const [rateLimit, setRateLimit] = useState(null);
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

  // 3. Persistance de l'historique à chaque changement (ORA-117)
  useEffect(() => {
    saveChatHistory(messages);
  }, [messages]);

  // 3. Envoi du message utilisateur (et ré-envoi, ORA-120)
  // `messageIndex` repère le message utilisateur associé dans `messages`,
  // pour pouvoir le marquer en échec (et l'en sortir au réessai) sans
  // dupliquer de bulle.
  const attemptSend = async (userMsg, messageIndex) => {
    setIsLoading(true);

    try {
      // Envoie le message + le contexte (prix, quartier...) au Backend
      const oracleResponse = await api.sendChatMessage(userMsg, buildChatContext(context, latestInsight));
      const responseText = typeof oracleResponse === 'string' ? oracleResponse : oracleResponse.response;

      // ORA-175 : la bulle garde les données structurées de sa réponse
      // (recommandations/compteur/filtre) — persistées avec le message dans
      // l'historique (sessionStorage), pas seulement dans `latestInsight`
      // (qui ne retient que la toute dernière réponse).
      const structured = typeof oracleResponse === 'object' ? oracleResponse : null;

      // Affiche la réponse d'Immotep, et lève le marqueur d'échec éventuel
      setMessages(prev => {
        const next = [...prev];
        if (next[messageIndex]?.sender === 'user') {
          next[messageIndex] = { ...next[messageIndex], failed: false };
        }
        return [...next, {
          sender: 'oracle',
          text: responseText,
          recommendations: structured?.recommendations,
          comparisons: structured?.comparisons,
          matchedCount: structured?.matched_count,
          parsed: structured?.parsed,
        }];
      });
      if (typeof oracleResponse === 'object') {
        setLatestInsight(oracleResponse);
        onInsight?.(oracleResponse);
        // ORA-118 : indicateur de quota, visible avant d'atteindre la limite
        if (oracleResponse.rateLimit) {
          setRateLimit(oracleResponse.rateLimit);
        }
      }
    } catch (error) {
      console.error('Erreur chat:', error);
      // ORA-120 : marque le message utilisateur en échec pour afficher un
      // bouton réessayer dessus (réseau, 500, timeout...)
      setMessages(prev => {
        const next = [...prev];
        if (next[messageIndex]?.sender === 'user') {
          next[messageIndex] = { ...next[messageIndex], failed: true };
        }
        return [...next, { sender: 'oracle', text: describeChatError(error) }];
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    const messageIndex = messages.length;

    // Affiche le message de l'utilisateur tout de suite
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setInput('');

    attemptSend(userMsg, messageIndex);
  };

  // ORA-120 : renvoie le même message (sans le ressaisir) depuis le bouton
  // réessayer affiché sur un message utilisateur en échec d'envoi.
  const handleRetry = (messageIndex, text) => {
    if (isLoading) return;
    setMessages(prev => {
      const next = [...prev];
      if (next[messageIndex]) {
        next[messageIndex] = { ...next[messageIndex], failed: false };
      }
      return next;
    });
    attemptSend(text, messageIndex);
  };

  // ORA-175 : puce de suggestion cliquable ("Et en T3 ?") — envoie le texte
  // comme un vrai message utilisateur, exactement comme handleSend.
  const handleSuggestionClick = (text) => {
    if (isLoading) return;
    const messageIndex = messages.length;
    setMessages(prev => [...prev, { sender: 'user', text }]);
    attemptSend(text, messageIndex);
  };

  return (
    <div className="flex flex-col h-full w-full bg-slate-950/50">
      
      {/* --- ZONE DE MESSAGES (Scrollable) --- */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5 custom-scrollbar">
        {messages.map((msg, idx) => (
          <div key={idx} data-testid="chat-message" data-sender={msg.sender} className={`flex w-full flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>

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

            {/* ORA-175 : résultats riches dans la bulle (maquette 07) — les
                comparaisons (intent "compare") priment sur les recommandations
                individuelles quand les deux sont présentes, comme l'ancien
                InsightPanel qu'elles remplacent (résultats désormais dans la
                bulle plutôt que dans un panneau séparé sous la zone de saisie). */}
            {msg.sender === 'oracle' && (msg.comparisons?.length > 0 || msg.recommendations?.length > 0) && (
              <div className="mt-2 w-full max-w-[88%] md:max-w-[82%] space-y-1.5">
                {(msg.comparisons?.length > 0 ? msg.comparisons : msg.recommendations).slice(0, 4).map((item, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 bg-ink-900 border border-ink-700 rounded-lg px-2.5 py-1.5 text-[11px]">
                    <span className="text-slate-300 truncate">
                      {item.quartier}
                      {item.type_local ? ` · ${item.type_local}` : ''}
                      {item.surface ? ` · ${item.surface} m²` : item.surface_moyenne ? ` · ${item.surface_moyenne} m² moy.` : ''}
                      {item.count ? ` · ${item.count} annonces` : ''}
                    </span>
                    <span className="font-bold text-white shrink-0">
                      {Math.round(item.prix ?? item.prix_moyen ?? 0).toLocaleString('fr-FR')} €
                    </span>
                  </div>
                ))}
                {!msg.comparisons?.length && msg.matchedCount > msg.recommendations.length && (
                  <button
                    type="button"
                    onClick={() => onListAnnonces?.(msg.recommendations[0]?.quartier)}
                    className="w-full text-[10px] uppercase tracking-widest font-bold text-violet-400 hover:text-violet-300 text-center py-1"
                  >
                    Lister les {msg.matchedCount} annonces →
                  </button>
                )}
              </div>
            )}

            {/* ORA-175 : suggestion contextuelle ("Et en T3 ?"), uniquement
                sur le tout dernier message pour ne pas encombrer l'historique. */}
            {msg.sender === 'oracle' && idx === messages.length - 1 && !isLoading && msg.parsed?.type_local && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {ALL_TYPES.filter((t) => t !== msg.parsed.type_local).slice(0, 2).map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => handleSuggestionClick(`Et en ${t} ?`)}
                    className="text-[10px] font-bold text-violet-300 bg-violet-900/30 border border-violet-700/50 rounded-full px-2.5 py-1 hover:bg-violet-900/50 transition-colors"
                  >
                    Et en {t} ?
                  </button>
                ))}
              </div>
            )}

            {/* ORA-120 : bouton réessayer sur le message utilisateur en échec d'envoi */}
            {msg.sender === 'user' && msg.failed && (
              <button
                type="button"
                onClick={() => handleRetry(idx, msg.text)}
                disabled={isLoading}
                data-testid="retry-button"
                className="mt-1 flex items-center gap-1 text-[11px] text-red-300 hover:text-red-200 underline underline-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Échec de l'envoi · Réessayer
              </button>
            )}
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
        {/* ORA-175 : les recommandations s'affichent désormais dans la bulle
            elle-même (maquette 07), plus dans un panneau séparé ici — l'ancien
            InsightPanel dupliquait ce que la bulle du dernier message montre déjà.
            `latestInsight` reste utile pour enrichir le contexte envoyé au
            prochain message (buildChatContext, plus bas). */}

        {/* Indicateur de Contexte (Si un scan est actif) */}
        {context && (
          <div className="flex items-center gap-2 mb-2 px-2 opacity-70">
            <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
              Secteur actif : {quartier || 'zone scannée'}
            </span>
          </div>
        )}

        {/* ORA-118 : quota restant, discret, visible avant d'atteindre le 429 */}
        {rateLimit && (
          <p data-testid="chat-quota" className="text-[9px] text-slate-600 mb-2 px-2 text-right">
            {rateLimit.remaining}{rateLimit.limit != null ? ` / ${rateLimit.limit}` : ''} question{rateLimit.limit > 1 ? 's' : ''} restante{rateLimit.limit > 1 ? 's' : ''} cette heure
          </p>
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
