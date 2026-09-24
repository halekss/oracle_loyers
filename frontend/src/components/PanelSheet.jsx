// ORA-178 : "feuille" de contenu du rail (maquette nav-b3-classeur) — chrome
// commun à toutes les vues (fond, bordure, coin haut-gauche carré pour se
// souder à l'onglet actif du rail, en-tête sur-titre/titre/actions). Le
// contenu de chaque vue (ResultCard, AnnoncesList, ChatOracle...) garde sa
// propre palette existante (ink-900/950) — seul le chrome de la feuille
// elle-même adopte la nouvelle palette du rail, pour ne pas reskinner des
// composants déjà stables/testés pour un gain visuel marginal.
export default function PanelSheet({ id, overline, title, actions, children }) {
  return (
    <section
      id={id}
      aria-label={title}
      className="flex-1 min-w-0 min-h-0 flex flex-col m-[14px] ml-0 rounded-[0_18px_18px_18px] border overflow-hidden"
      style={{ background: '#151C33', borderColor: '#232B45', borderRadius: '0 18px 18px 18px' }}
    >
      {(overline || title || actions) && (
        <header className="shrink-0 flex items-start justify-between gap-3 px-4 md:px-5 py-3.5 border-b" style={{ borderColor: '#1C2440' }}>
          <div className="min-w-0">
            {overline && (
              <p className="text-[10px] font-bold uppercase tracking-widest truncate" style={{ color: '#A78BFA' }}>
                {overline}
              </p>
            )}
            {title && <h2 className="text-lg font-black mt-0.5 truncate" style={{ color: '#F1F5F9' }}>{title}</h2>}
          </div>
          {actions && <div className="shrink-0 flex items-center gap-2">{actions}</div>}
        </header>
      )}

      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
        {children}
      </div>
    </section>
  );
}
