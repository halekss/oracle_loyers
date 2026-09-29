// ORA-198 : un état visuel explicite par cas où l'estimation du modèle
// n'est pas possible ou pas fiable, au lieu d'un échec silencieux ou d'un
// message générique unique. `code` vient directement du contrat /api/predict
// (NO_SURFACE, UNKNOWN_QUARTIER, IMPLAUSIBLE, MODEL_UNAVAILABLE) — jamais de
// texte à parser. `LOW_SAMPLE` n'a pas d'entrée ici : ce cas n'empêche pas
// l'estimation de s'afficher (badge "Confiance IA : Faible" déjà existant
// dans ResultCard), donc pas de carte de statut bloquante à afficher.
const STATUS_CONFIG = {
  NO_SURFACE: {
    icon: '📐',
    title: 'Surface manquante',
    message: "Ajoute une surface pour obtenir l'estimation du modèle.",
    actionLabel: 'Aller à Recherche',
  },
  UNKNOWN_QUARTIER: {
    icon: '📍',
    title: 'Quartier pas encore connu du modèle',
    message: 'Le modèle ne connaît pas encore ce quartier. Voici la médiane réelle des annonces.',
  },
  IMPLAUSIBLE: {
    icon: '⚠️',
    title: 'Estimation impossible',
    message: 'Estimation impossible pour ces critères.',
    actionLabel: 'Modifier les critères',
  },
  MODEL_UNAVAILABLE: {
    icon: '🔌',
    title: 'Oracle indisponible',
    message: "L'Oracle est momentanément indisponible.",
    actionLabel: 'Réessayer',
  },
};

const formatEuros = (value) => (Number.isFinite(value) ? value.toLocaleString('fr-FR', { maximumFractionDigits: 0 }) : null);

export default function EstimationStatus({ code, medianPrice, medianPriceM2, onAction }) {
  const config = STATUS_CONFIG[code];
  if (!config) return null;

  const formattedPrice = formatEuros(medianPrice);
  const formattedPriceM2 = formatEuros(medianPriceM2);

  return (
    <div role="status" className="p-4 md:p-5 rounded-xl border" style={{ background: '#0F1630', borderColor: '#232B45' }}>
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="text-xl leading-none shrink-0">{config.icon}</span>
        <div className="min-w-0">
          <h3 className="text-sm font-bold text-white">{config.title}</h3>
          <p className="mt-1 text-xs text-ink-dim">{config.message}</p>
          {code === 'UNKNOWN_QUARTIER' && formattedPrice && (
            <p className="mt-2 text-sm font-bold text-white">
              Médiane réelle : {formattedPrice} €{formattedPriceM2 && ` (${formattedPriceM2} €/m²)`}
            </p>
          )}
          {config.actionLabel && (
            <button
              type="button"
              onClick={onAction}
              className="mt-3 text-[10px] uppercase tracking-widest font-bold text-accent-light hover:text-accent-light transition-colors underline decoration-accent/40 underline-offset-2"
            >
              {config.actionLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
