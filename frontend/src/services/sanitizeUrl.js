// Ne garde que les URL http(s) valides avant d'ouvrir un lien externe issu
// de données scrapées (AnnonceCard.jsx, AnnonceDetailModal.jsx) — même
// logique que sanitize_listing_url (backend/scripts/generate_map.py),
// jusqu'ici dupliquée seulement côté Python, jamais côté React (ORA-126).
export function sanitizeListingUrl(url) {
  if (typeof url !== 'string') return null;
  const candidate = url.trim();
  if (!candidate) return null;
  const lowered = candidate.toLowerCase();
  if (lowered.startsWith('http://') || lowered.startsWith('https://')) {
    return candidate;
  }
  return null;
}
