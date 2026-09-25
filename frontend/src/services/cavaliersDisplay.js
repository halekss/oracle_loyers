// Dérive l'affichage des lignes "cavaliers" de la vue Calques (maquette
// vue-calques.png) à partir de `cavaliers_detail` (déjà calculé côté backend,
// services/cavaliers_factors.py::detail_cavaliers) — jamais recalculé ici.

// Le backend n'expose la distance du lieu le plus proche, quand une
// catégorie est vide, que dans la phrase `empty_message` ("... à 573 m.") —
// on l'extrait plutôt que de demander un nouveau champ API pour ce seul
// affichage.
function parseClosestDistance(emptyMessage) {
  if (!emptyMessage) return null;
  const match = emptyMessage.match(/à (\d+)\s*m\.?$/);
  return match ? Number(match[1]) : null;
}

function minDistance(items) {
  const distances = (items || []).map((item) => item.dist_m).filter((d) => d != null);
  return distances.length ? Math.min(...distances) : null;
}

// { count, distM } pour composer "N lieux · dès X m" (count > 0) ou
// "0 · le 1er à X m" (count === 0) — cf. vue-calques.png.
export function cavalierMeta(cat) {
  if (!cat) return null;
  if (cat.total > 0) {
    return { count: cat.total, distM: minDistance(cat.items) };
  }
  return { count: 0, distM: parseClosestDistance(cat.empty_message) };
}

// Forme + couleur de chacun des 4 cavaliers (maquette vue-calques.png) —
// partagées entre la vue Calques (CavalierRow) et la légende "Cavaliers
// affichés" de la carte (MapComponent), pour ne jamais les définir deux fois.
export const CAVALIER_STYLES = [
  { categorie: 'Vice', color: '#F87171', shape: 'circle' },
  { categorie: 'Gentrification', color: '#C084FC', shape: 'diamond' },
  { categorie: 'Nuisance', color: '#FB923C', shape: 'triangle' },
  { categorie: 'Superstition', color: '#CBD5E1', shape: 'square' },
];

// Rayon des cavaliers (mètres) : seul rayon précalculé côté backend
// (services/cavaliers_factors.py) — cf. sélecteur 300 m/500 m/1 km de la vue
// Calques (500 m seul actif) et cercle tracé sur la carte.
export const CAVALIERS_RADIUS_M = 500;

// Catégorie dépliée par défaut (une seule à la fois) : celle qui compte le
// plus de lieux. `null` sans détail (aucun scan encore lancé).
export function defaultExpandedCategory(cavaliersDetail) {
  if (!cavaliersDetail || cavaliersDetail.length === 0) return null;
  return cavaliersDetail.reduce(
    (best, cat) => (cat.total > (best?.total ?? -1) ? cat : best),
    null,
  )?.categorie ?? null;
}
