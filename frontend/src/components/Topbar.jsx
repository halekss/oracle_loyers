// ORA-179 : barre supérieure allégée (maquette nav-b3v2-recherche) — ne
// garde que le logo et le badge de fraîcheur des données. Toute la
// recherche (ville, quartier, type, surface, scan) a déménagé dans
// SearchForm, vivant désormais dans la vue "Recherche" du rail (desktop) ou
// en haut de la colonne Oracle mobile — plus dans cette barre, persistante
// mais volontairement vide sinon (ORA-170).
export default function Topbar({ dataAsOf }) {
  return (
    <header className="shrink-0 h-14 bg-ink-950 border-b border-ink-800 px-3 md:px-4 flex items-center justify-between gap-2">
      <span className="font-display font-extrabold text-sm md:text-base tracking-tight text-white shrink-0">
        ORACLE <span className="text-violet-500">DES LOYERS</span>
      </span>

      {dataAsOf && (
        <div className="flex items-center gap-1.5 shrink-0 px-2.5 py-1.5 rounded-lg bg-ink-900 border border-ink-700 text-[10px] text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
          <span className="uppercase tracking-widest font-bold text-slate-500">Données au</span>
          <span className="text-slate-300 font-semibold">{dataAsOf}</span>
        </div>
      )}
    </header>
  );
}
