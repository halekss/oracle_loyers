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
