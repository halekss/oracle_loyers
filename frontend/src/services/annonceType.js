// `annonces.db` ne stocke pas de colonne `type_local` séparée, mais
// `build_titre` (clean_immo.py) préfixe déjà le titre avec elle
// ("T3 — Monplaisir / Bachut") : on la lit là en priorité, pour rester
// cohérent avec le type réellement affiché dans le titre de la carte (basé
// sur le texte de l'annonce, plus fiable que la seule surface). Fallback sur
// les seuils de surface de `determine_type_local` si le titre ne la contient
// pas (annonce sans quartier, titre de repli sur la description...).
//
// Fichier séparé de AnnonceCard.jsx (ORA-173) : react-refresh interdit
// d'exporter une fonction utilitaire depuis un fichier de composant, et
// AnnoncesList.jsx en a aussi besoin (tri "Meilleures affaires").
const KNOWN_CATEGORIES = ['Studio/T1', 'T2', 'T3', 'Grand (T4+)'];

export const getTypeCategory = (titre, surface) => {
  if (typeof titre === 'string') {
    const prefix = titre.split(' — ')[0].trim();
    if (KNOWN_CATEGORIES.includes(prefix)) return prefix;
  }

  const s = Number(surface);
  if (!Number.isFinite(s)) return null;
  if (s < 35) return 'Studio/T1';
  if (s < 55) return 'T2';
  if (s < 75) return 'T3';
  return 'Grand (T4+)';
};

// `annonces` (SQLite) ne stocke pas la source du scrape — dérivée du nom de
// domaine de `url` (les scrapers sont nommés à l'identique, cf.
// backend/scripts/scraper_*.py), plutôt qu'une colonne à ajouter pour un
// simple libellé d'affichage (ORA-173, réutilisé par ORA-174).
const SOURCE_BY_HOST = {
  'vizzit.fr': 'Vizzit',
  'www.vizzit.fr': 'Vizzit',
  'pap.fr': 'PAP',
  'www.pap.fr': 'PAP',
  'seloger.com': 'SeLoger',
  'www.seloger.com': 'SeLoger',
  'century21.fr': 'Century 21',
  'www.century21.fr': 'Century 21',
  'paruvendu.fr': 'ParuVendu',
  'www.paruvendu.fr': 'ParuVendu',
  'orpi.com': 'Orpi',
  'www.orpi.com': 'Orpi',
};

export function deriveSource(url) {
  if (typeof url !== 'string') return null;
  try {
    return SOURCE_BY_HOST[new URL(url).hostname] || null;
  } catch {
    return null;
  }
}
