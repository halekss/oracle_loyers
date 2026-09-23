import { useCallback, useEffect, useState } from 'react';
import { loadFavoriteIds, saveFavoriteIds } from '../services/favoritesStorage';

// ORA-132 : favoris ("Mes favoris") persistés en localStorage uniquement -
// décision de cadrage produit : pas de compte utilisateur / backend
// (l'app n'a aujourd'hui aucune notion de session persistante, cf. ticket
// ORA-132 ; localStorage est explicitement l'option la plus légère listée
// et la seule cohérente avec l'architecture actuelle sans auth). Le jour où
// des comptes utilisateurs existeront, cette persistance pourra être
// remplacée sans changer l'API exposée par ce hook (isFavorite/toggleFavorite).
const FAVORITES_CHANGED_EVENT = 'oracle-loyers:favorites-changed';

export function useFavorites() {
  const [favoriteIds, setFavoriteIds] = useState(() => new Set(loadFavoriteIds()));

  // Plusieurs instances de ce hook peuvent être montées en même temps
  // (chaque AnnonceCard + le filtre "Mes favoris" de AnnoncesList). Un
  // événement custom les garde synchronisées dans le même onglet - les
  // événements natifs "storage" ne se déclenchent que dans les *autres*
  // onglets, jamais dans celui qui a fait l'écriture.
  //
  // L'événement transporte directement la liste d'ids à jour (`detail`)
  // plutôt que de faire relire localStorage à chaque instance : si
  // localStorage est indisponible (navigation privée stricte, quota...),
  // une relecture retomberait toujours sur une liste vide et écraserait
  // l'état en mémoire qu'on veut justement garder utilisable pour la
  // session courante (cf. edge case testée dans useFavorites.test.js).
  useEffect(() => {
    const handleChange = (e) => setFavoriteIds(new Set(e.detail));
    window.addEventListener(FAVORITES_CHANGED_EVENT, handleChange);
    return () => window.removeEventListener(FAVORITES_CHANGED_EVENT, handleChange);
  }, []);

  const isFavorite = useCallback((id) => id != null && favoriteIds.has(id), [favoriteIds]);

  const toggleFavorite = useCallback((id) => {
    if (id == null) return;
    const next = new Set(favoriteIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    saveFavoriteIds(Array.from(next));
    setFavoriteIds(next);
    window.dispatchEvent(new CustomEvent(FAVORITES_CHANGED_EVENT, { detail: Array.from(next) }));
  }, [favoriteIds]);

  return { favoriteIds, isFavorite, toggleFavorite };
}
