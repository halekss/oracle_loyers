// ORA-171 : badge "DONNÉES AU" de la topbar (maquette 03, repris sur toutes
// les vues) — date de la donnée la plus récente pour la ville active.
//
// `date_dernier_scan` (ORA-147, diff de scrape à 2 états) n'existe que pour
// les annonces scrapées avec ce champ : actuellement Lille uniquement, Lyon
// n'en a aucune (pipeline plus ancien). Renvoie `null` plutôt qu'une date
// inventée quand la ville active n'a aucune valeur exploitable.
export function computeLatestDataDate(listings, ville) {
  const dates = (listings || [])
    .filter((item) => (item.ville || '').toLowerCase() === (ville || '').toLowerCase())
    .map((item) => item.date_dernier_scan)
    .filter((d) => typeof d === 'string' && d.length > 0);

  if (dates.length === 0) return null;

  const latest = dates.reduce((max, d) => (d > max ? d : max));
  const parsed = new Date(latest);
  if (Number.isNaN(parsed.getTime())) return null;

  return parsed.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}
