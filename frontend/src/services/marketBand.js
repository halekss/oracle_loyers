import config from '../config/marketBands.config.json';

// Écart d'un loyer à la référence du quartier → bande de marché (ORA-165/168).
// Seuil et couleurs dans marketBands.config.json, lu aussi par
// backend/scripts/generate_map.py : carte et panneau restent cohérents.
// Bornes : < -seuil = sous le marché, > +seuil = au-dessus, sinon dans le marché.
export const MARKET_BANDS = config.bands;

export function marketBand(ecartPct) {
  if (ecartPct < -config.thresholdPct) return 'below';
  if (ecartPct > config.thresholdPct) return 'above';
  return 'within';
}

// Classes Tailwind littérales (pas de concaténation : Tailwind ne détecterait
// pas les classes construites dynamiquement).
export const BAND_BADGE_CLASSES = {
  below: 'bg-market-below/15 text-market-below',
  within: 'bg-market-within/15 text-market-within',
  above: 'bg-market-above/15 text-market-above',
};

// Écart en % de `prixM2` vs `referencePrixM2`, arrondi ; null si non calculable.
export function ecartPct(prixM2, referencePrixM2) {
  if (!Number.isFinite(prixM2) || !Number.isFinite(referencePrixM2) || referencePrixM2 <= 0) return null;
  return Math.round(((prixM2 - referencePrixM2) / referencePrixM2) * 100);
}
