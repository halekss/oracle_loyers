import React, { useState, useEffect } from "react";
import { api, describeApiError } from "../services/api";
import { downloadBlob } from "../services/downloadBlob";
import { BAND_BADGE_CLASSES, MARKET_BANDS, ecartPct, marketBand } from "../services/marketBand";
import { computeVilleMedianPrice } from "../services/estimationChart";

const VILLE_LABELS = { lyon: { nom: 'Lyon', gentile: 'lyonnaises' }, lille: { nom: 'Lille', gentile: 'lilloises' } };
// ORA-190 : bornes et debounce du slider de surface (panneau "Estimation
// personnalisée") — remplace les 3 scénarios à delta fixe (-15/=/+15, ORA-171)
// par un contrôle continu.
const SLIDER_MIN_SURFACE = 10;
const SLIDER_MAX_SURFACE = 150;
const SLIDER_DEBOUNCE_MS = 300;

const formatPrice = (p) => (p ? Math.round(p).toLocaleString('fr-FR') : "--");
const formatM2 = (p) => (p ? p.toLocaleString('fr-FR', { maximumFractionDigits: 1 }) : "--");

const formatShortDate = (d) => new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });

// Période couverte par les snapshots de l'historique (ORA-167) : "03/08 → 14/08".
function historyPeriod(historique) {
  const dates = (historique || []).map((p) => p.date).filter(Boolean).sort();
  if (dates.length < 2) return null;
  return `${formatShortDate(dates[0])} → ${formatShortDate(dates[dates.length - 1])}`;
}

// Position (0-100 %) d'une valeur sur la barre min → max.
const positionOnRange = (v, min, max) => (max > min ? ((v - min) / (max - min)) * 100 : 50);

const RANGE_LABELS = [['min', 'Min'], ['p25', 'P25'], ['mediane', 'Médiane'], ['p75', 'P75'], ['max', 'Max']];

// `onViewAnnonces` (optionnel, ORA-127) : appelé avec le quartier scanné
// (`data.quartier`) quand l'utilisateur clique le lien direct vers ses
// annonces — le parent (App) s'en sert pour présélectionner AnnoncesList.
// `ville`/`health` (ORA-171) : alimentent "± N € (erreur moyenne du modèle
// XGBoost <Ville>)" et "entraîné sur N annonces" avec les vraies métriques
// du modèle actif plutôt que des chiffres codés en dur.
// `dataAsOf` (ORA-177) : badge "Données au" déjà calculé pour la Topbar,
// repris tel quel dans l'en-tête du rapport PDF exporté.
// `listings` (ORA-190, optionnel) : payload brut de /api/listings, déjà
// chargé par App.jsx — sert uniquement à calculer la médiane ville (même
// type de bien) du bar chart d'estimation, sans nouvel appel réseau.
export default function ResultCard({ data, loading, priceHistory, onViewAnnonces, onAddSurface, ville, health, dataAsOf, listings }) {

  const safeData = data || {};
  const stats = safeData.stats || {};

  const estimatedPrice = safeData.estimated_price || 0;
  const m2PriceRaw = stats.prix_m2 || 0;
  const confiance = safeData.confiance;
  const quartier = safeData.quartier;
  const facteurs = safeData.facteurs || [];
  // ORA-177 : le backend renvoie désormais jusqu'à 12 comparables (pour le
  // tableau du rapport PDF) — l'affichage à l'écran reste volontairement
  // compact (3 max), le PDF exporte la liste complète `comparables`.
  const comparables = safeData.comparables || [];
  const onScreenComparables = comparables.slice(0, 3);
  const surface = safeData.surface;
  const prixStats = safeData.prixStats;
  const period = historyPeriod(priceHistory?.historique);
  // ORA-171 : le panneau "Estimation personnalisée" (maquette 03) ne
  // s'affiche que si une vraie prédiction XGBoost a eu lieu (surface +
  // type précis fournis) — sinon on garde l'affichage "moyenne du secteur"
  // existant (scan sans surface, périmètre ORA-167/epic ORA-162).
  const hasModelEstimate = Boolean(surface) && Boolean(confiance);

  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);
  // ORA-190 : slider de surface (remplace les 3 scénarios à delta fixe
  // -15/=/+15 d'ORA-171) — `sliderSurface` piloté par l'utilisateur,
  // `sliderEstimate` la dernière prédiction connue pour cette valeur.
  const [sliderSurface, setSliderSurface] = useState(surface || SLIDER_MIN_SURFACE);
  const [sliderEstimate, setSliderEstimate] = useState(null);
  const [sliderLoading, setSliderLoading] = useState(false);
  const [sliderError, setSliderError] = useState(null);

  const confidenceStyles = {
    'Élevée': 'bg-green-900/40 text-green-400 border-green-700/50',
    'Moyenne': 'bg-amber-900/40 text-amber-400 border-amber-700/50',
    'Faible': 'bg-red-900/40 text-red-400 border-red-700/50',
  };

  // Un nouveau scan (nouvelle surface/quartier/type) remet le slider sur la
  // surface réellement scannée plutôt que de garder la position précédente.
  useEffect(() => {
    if (hasModelEstimate) setSliderSurface(surface);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasModelEstimate, surface, quartier, safeData.type]);

  // ORA-190 : au plus un appel `predict` par pause de saisie (debounce), et
  // aucun appel pour la surface déjà connue (`estimatedPrice`, comme l'ancien
  // mécanisme de scénarios ORA-171). Une prédiction en erreur ne casse pas le
  // reste du panneau (pas de barre fantôme : `sliderEstimate` reste `null`
  // tant qu'aucune valeur valide n'est connue pour la surface courante).
  useEffect(() => {
    if (!hasModelEstimate) {
      setSliderEstimate(null);
      setSliderError(null);
      return;
    }
    if (sliderSurface === surface) {
      setSliderEstimate(estimatedPrice);
      setSliderError(null);
      setSliderLoading(false);
      return;
    }

    let cancelled = false;
    setSliderLoading(true);
    setSliderError(null);

    const timer = setTimeout(() => {
      api.predict({ surface: sliderSurface, quartier, type_local: safeData.type })
        .then((r) => {
          if (cancelled) return;
          if (typeof r.estimated_price === 'number') {
            setSliderEstimate(r.estimated_price);
          } else {
            setSliderEstimate(null);
            setSliderError("Estimation indisponible pour cette surface.");
          }
        })
        .catch(() => {
          if (!cancelled) {
            setSliderEstimate(null);
            setSliderError("Estimation indisponible pour cette surface.");
          }
        })
        .finally(() => {
          if (!cancelled) setSliderLoading(false);
        });
    }, SLIDER_DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasModelEstimate, sliderSurface, surface, quartier, safeData.type]);

  // ORA-190 : 3e repère du bar chart (médiane ville, même type de bien) —
  // médiane quartier déjà fournie par prixStats (/api/quartier-stats).
  const villeMedianPrice = hasModelEstimate
    ? computeVilleMedianPrice(listings, ville, safeData.type)
    : null;

  // ORA-121 : génération PDF côté serveur (WeasyPrint) + téléchargement
  // direct, plus de window.print()/sélecteur d'impression système.
  const handleExportPdf = async () => {
    setExporting(true);
    setExportError(null);

    try {
      const blob = await api.exportEstimationPdf({
        quartier,
        estimated_price: estimatedPrice,
        prix_m2: m2PriceRaw,
        confiance,
        count: safeData.count,
        type_local: safeData.type,
        surface: hasModelEstimate ? surface : undefined,
        data_as_of: dataAsOf || undefined,
        facteurs,
        historique: priceHistory?.historique || undefined,
        comparables: comparables.length > 0 ? comparables : undefined,
      });
      const slug = (quartier || 'estimation').toLowerCase().replace(/[^a-z0-9]+/g, '-');
      downloadBlob(blob, `rapport-oracle-${slug}.pdf`);
    } catch (err) {
      console.error(err);
      setExportError(describeApiError(err));
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse w-full space-y-3">
        <div className="flex gap-3">
           <div className="h-20 bg-slate-800 rounded-xl w-2/3"></div>
           <div className="h-20 bg-slate-800 rounded-xl w-1/3"></div>
        </div>
      </div>
    );
  }

  if (hasModelEstimate) {
    const villeInfo = VILLE_LABELS[ville] || VILLE_LABELS.lyon;
    const metrics = health?.models?.[villeInfo.nom]?.metrics;
    const mae = metrics?.mae;
    const datasetSize = metrics?.dataset_size;

    // ORA-190 : bar chart — estimation du modèle (surface courante du
    // slider) vs médiane du quartier (même type, prixStats déjà fourni par
    // /api/quartier-stats) vs médiane ville (même type, computeVilleMedianPrice).
    // Un repère sans valeur connue est simplement omis (pas de barre fantôme).
    const chartBars = [
      { key: 'modele', label: 'Estimation modèle', value: sliderEstimate, color: '#eab308' },
      { key: 'quartier', label: `Médiane ${safeData.type} · ${quartier}`, value: prixStats?.mediane ?? null, color: '#a78bfa' },
      { key: 'ville', label: `Médiane ${safeData.type} · ${villeInfo.nom}`, value: villeMedianPrice, color: '#38bdf8' },
    ].filter((bar) => bar.value != null);
    const maxBarValue = chartBars.length > 0 ? Math.max(...chartBars.map((b) => b.value)) * 1.1 : 0;

    return (
      <div className="w-full animate-fade-in">
        <div className="flex items-start justify-between mb-3">
          <div>
            <p className="text-[10px] uppercase text-violet-400 font-bold tracking-widest">
              {quartier} · {safeData.type} · {surface} m²
            </p>
            <h2 className="text-lg font-black text-white mt-0.5">Estimation personnalisée</h2>
          </div>
          <button
            type="button"
            onClick={handleExportPdf}
            disabled={exporting}
            aria-label="Exporter en PDF"
            className="shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 bg-ink-900 border border-ink-700 rounded-lg text-[10px] font-bold uppercase text-slate-300 hover:border-violet-500 transition-colors disabled:opacity-50"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            {exporting ? '…' : 'PDF'}
          </button>
        </div>

        {/* Carte principale : estimation + prix/m² pour la surface du slider */}
        <div className="bg-ink-900 border border-ink-700 rounded-xl p-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1">
                Estimation modèle · {sliderSurface} m²
              </p>
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-black text-white" aria-live="polite">
                  {sliderEstimate != null ? formatPrice(sliderEstimate) : (sliderLoading ? '…' : '--')}
                </span>
                <span className="text-base text-slate-500">€</span>
              </div>
              {mae != null && sliderEstimate != null && (
                <p className="mt-1 text-[10px] text-slate-500">
                  ± {formatPrice(mae)} € (erreur moyenne du modèle XGBoost {villeInfo.nom})
                </p>
              )}
              {sliderError && (
                <p className="mt-1 text-[10px] text-red-400">{sliderError}</p>
              )}
            </div>
            <div className="text-right">
              <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1">Prix m²</p>
              <div className="text-xl font-black text-yellow-400">
                {sliderEstimate != null ? formatM2(sliderEstimate / sliderSurface) : '--'} €
              </div>
              {safeData.quartierPrixM2 != null && (
                <p className="mt-1 text-[10px] text-slate-500">
                  médiane {safeData.type} : {formatM2(safeData.quartierPrixM2)} €
                </p>
              )}
            </div>
          </div>

          {/* ORA-190 : slider continu (remplace les 3 scénarios -15/=/+15 d'ORA-171) */}
          <div className="mt-3">
            <label
              htmlFor="estimation-surface-slider"
              className="flex items-center justify-between text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1.5"
            >
              <span>Simuler une autre surface</span>
              <span className="text-slate-300 normal-case">{sliderSurface} m²</span>
            </label>
            <input
              id="estimation-surface-slider"
              type="range"
              min={SLIDER_MIN_SURFACE}
              max={SLIDER_MAX_SURFACE}
              value={sliderSurface}
              onChange={(e) => setSliderSurface(Number(e.target.value))}
              className="w-full accent-violet-500"
            />
            <div className="flex justify-between text-[9px] text-slate-500">
              <span>{SLIDER_MIN_SURFACE} m²</span>
              <span>{SLIDER_MAX_SURFACE} m²</span>
            </div>
          </div>
        </div>

        {/* ORA-190 : estimation vs médiane quartier vs médiane ville — un
            repère toujours lisible en texte, avec ou sans la barre elle-même
            (accessibilité, ORA-190). */}
        {(chartBars.length > 0 || sliderLoading) && (
          <div className="mt-3 bg-ink-900 border border-ink-700 rounded-xl p-3">
            <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-2">
              Estimation vs marché
            </p>
            {chartBars.length === 0 && sliderLoading && (
              <div className="animate-pulse space-y-1.5">
                <div className="h-2 bg-ink-800 rounded-full w-full" />
                <div className="h-2 bg-ink-800 rounded-full w-2/3" />
              </div>
            )}
            <div className="space-y-2.5">
              {chartBars.map((bar) => (
                <div key={bar.key}>
                  <div className="flex items-baseline justify-between gap-2 text-[10px] mb-1">
                    <span className="text-slate-400 truncate">{bar.label}</span>
                    <span className="shrink-0 font-bold text-slate-200">{formatPrice(bar.value)} €</span>
                  </div>
                  <div className="h-2 bg-ink-800 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-[width] duration-300"
                      style={{
                        width: `${maxBarValue > 0 ? (bar.value / maxBarValue) * 100 : 0}%`,
                        backgroundColor: bar.color,
                        opacity: bar.key === 'modele' && sliderLoading ? 0.5 : 1,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Comment l'Oracle calcule */}
        <div className="mt-3 bg-ink-900 border border-ink-700 rounded-xl p-3">
          <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-2">
            Comment l'Oracle calcule
          </p>
          <ol className="space-y-1.5 text-[11px] text-slate-300">
            <li><span className="text-violet-400 font-bold mr-1.5">1</span>Surface, type, position et distances aux 4 cavaliers.</li>
            <li>
              <span className="text-violet-400 font-bold mr-1.5">2</span>
              XGBoost entraîné sur {datasetSize != null ? datasetSize.toLocaleString('fr-FR') : '—'} annonces {villeInfo.gentile}.
            </li>
            <li><span className="text-violet-400 font-bold mr-1.5">3</span>Fourchette = erreur moyenne sur des annonces test.</li>
          </ol>
        </div>

        {/* Surfaces proches · écart à l'estimation */}
        {onScreenComparables.length > 0 && (
          <div className="mt-3 bg-ink-900 border border-ink-700 rounded-xl p-3">
            <div className="flex items-center justify-between mb-1.5">
              <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold">
                Surfaces proches · écart à l'estimation
              </p>
              {onViewAnnonces && safeData.count != null && (
                <button
                  type="button"
                  onClick={() => onViewAnnonces(quartier)}
                  className="text-[9px] uppercase tracking-widest font-bold text-violet-400 hover:text-violet-300"
                >
                  Voir les {safeData.count} →
                </button>
              )}
            </div>
            <ul className="space-y-1">
              {onScreenComparables.map((c, i) => {
                const expected = m2PriceRaw * c.surface;
                const ecart = expected > 0 ? Math.round(((c.prix - expected) / expected) * 100) : null;
                return (
                  <li key={i} className="flex items-center justify-between text-[11px] text-slate-300">
                    <span>{c.type_local || '—'} · {formatPrice(c.surface)} m²</span>
                    <span className="flex items-center gap-2">
                      <span className="font-bold text-white">{formatPrice(c.prix)} €</span>
                      {ecart !== null && (
                        <span className={ecart > 0 ? 'text-red-400' : 'text-green-400'}>
                          {ecart > 0 ? '+' : ''}{ecart} %
                        </span>
                      )}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {exportError && (
          <p className="mt-2 text-[10px] text-red-400 font-bold bg-red-900/20 p-2 rounded border border-red-900/50">
            Erreur lors de l'export PDF : {exportError}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="w-full animate-fade-in">

      {/* SECTION PRIX PRINCIPALE */}
      <div className="flex gap-3">

        {/* GROS BLOC : LOYER */}
        <div className="flex-1 bg-gradient-to-br from-ink-800 to-ink-900 p-4 rounded-xl border border-accent/20 shadow-[0_4px_20px_rgba(0,0,0,0.2)] relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-2 opacity-5 text-6xl font-black text-white pointer-events-none">€</div>

          <div className="flex justify-between items-start">
            <div>
                <p className="text-[10px] uppercase text-accent-light font-bold tracking-widest mb-1">Estimation Loyer</p>
                <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-black text-white tracking-tighter shadow-black drop-shadow-lg">
                    {formatPrice(estimatedPrice)}
                    </span>
                    <span className="text-lg text-ink-dim">€</span>
                </div>
            </div>
            {confiance && (
              <span
                className={`text-[9px] uppercase font-bold tracking-wide px-2 py-1 rounded-full border ${confidenceStyles[confiance] || 'bg-ink-800 text-ink-muted border-ink-700'}`}
                title={safeData.count != null ? `Basée sur ${safeData.count} bien(s) comparable(s) du même quartier et type` : undefined}
              >
                Confiance IA : {confiance}
              </span>
            )}
          </div>
          {/* ORA-128 : explique la confiance plutôt que de la laisser abstraite */}
          {safeData.count != null && (
            <p className="mt-2 text-[9px] text-ink-dim">
              Basée sur {safeData.count} bien{safeData.count > 1 ? 's' : ''} comparable{safeData.count > 1 ? 's' : ''} du même quartier et type.
            </p>
          )}
          {/* ORA-127 : lien direct depuis le quartier scanné vers ses annonces */}
          {quartier && onViewAnnonces && (
            <button
              type="button"
              onClick={() => onViewAnnonces(quartier)}
              className="mt-2 text-[9px] uppercase tracking-widest font-bold text-accent-light hover:text-accent-light transition-colors underline decoration-accent/40 underline-offset-2"
            >
              Voir les annonces de {quartier} →
            </button>
          )}
          {/* ORA-167 : ouvre la saisie de surface pour l'estimation modèle */}
          {onAddSurface && !surface && (
            <button
              type="button"
              onClick={onAddSurface}
              className="mt-2 ml-3 text-[9px] uppercase tracking-widest font-bold text-ink border border-accent/60 rounded px-1.5 py-0.5 hover:bg-accent/20 transition-colors"
            >
              + Surface
            </button>
          )}
        </div>

        {/* PETIT BLOC : PRIX M2 */}
        <div className="w-1/3 bg-ink-900 p-3 rounded-xl border border-ink-700 flex flex-col justify-center items-center relative">
          <p className="text-[9px] uppercase text-ink-dim font-bold mb-1">Prix m²</p>
          <div className="text-xl font-bold text-yellow-400 font-mono">
            {formatPrice(m2PriceRaw)}
          </div>
          <p className="text-[9px] text-ink-dim mt-1">Moyenne</p>
        </div>
      </div>

      {prixStats && (
        <div className="mt-3 bg-ink-900 rounded-xl border border-ink-700 p-3" data-testid="price-range">
          <div className="flex items-center justify-between mb-3">
            <p className="text-[9px] uppercase text-ink-dim font-bold tracking-widest">Fourchette des loyers</p>
            {period && <p className="text-[9px] text-ink-dim">{period}</p>}
          </div>
          <div className="relative h-1.5 bg-ink-800 rounded-full">
            <div
              className="absolute inset-y-0 bg-accent/60 rounded-full"
              style={{
                left: `${positionOnRange(prixStats.p25, prixStats.min, prixStats.max)}%`,
                width: `${positionOnRange(prixStats.p75, prixStats.min, prixStats.max) - positionOnRange(prixStats.p25, prixStats.min, prixStats.max)}%`,
              }}
            />
            <div
              className="absolute -top-1 w-3.5 h-3.5 rounded-full bg-market-within border-2 border-ink-900 -translate-x-1/2"
              style={{ left: `${positionOnRange(prixStats.mediane, prixStats.min, prixStats.max)}%` }}
              title={`Médiane : ${formatPrice(prixStats.mediane)} €`}
            />
          </div>
          <dl className="mt-3 grid grid-cols-5 text-center">
            {RANGE_LABELS.map(([key, label]) => (
              <div key={key}>
                <dd className={`text-[11px] font-bold ${key === 'mediane' ? 'text-market-within' : 'text-ink'}`}>{formatPrice(prixStats[key])}</dd>
                <dt className="text-[8px] uppercase tracking-wide text-ink-dim">{label}</dt>
              </div>
            ))}
          </dl>
        </div>
      )}

      {onScreenComparables.length > 0 && (
        <div className="mt-3 bg-ink-900 rounded-xl border border-ink-700 p-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[9px] uppercase text-ink-dim font-bold tracking-widest">Annonces représentatives</p>
            {onViewAnnonces && safeData.count != null && (
              <button
                type="button"
                onClick={() => onViewAnnonces(quartier)}
                className="text-[9px] uppercase tracking-widest font-bold text-accent-light hover:text-ink transition-colors"
              >
                Voir les {safeData.count} →
              </button>
            )}
          </div>
          <ul className="space-y-1.5">
            {onScreenComparables.map((c, i) => {
              const prixM2 = c.surface > 0 ? c.prix / c.surface : null;
              const ecart = ecartPct(prixM2, m2PriceRaw);
              const band = ecart != null ? marketBand(ecart) : null;
              return (
                <li key={i} className="flex items-center justify-between gap-2 text-[11px] text-ink bg-ink-800/60 rounded-lg px-2.5 py-1.5">
                  <span className="min-w-0 truncate">
                    <span className="font-bold">{c.type_local || '—'}</span>
                    <span className="text-ink-muted"> · {formatPrice(c.surface)} m²{prixM2 != null && ` · ${formatM2(prixM2)} €/m²`}</span>
                  </span>
                  <span className="shrink-0 flex items-center gap-2">
                    <span className="font-bold">{formatPrice(c.prix)} €</span>
                    {ecart != null && (
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${BAND_BADGE_CLASSES[band]}`}
                        title={`${MARKET_BANDS[band].label} — écart vs €/m² moyen du quartier`}
                      >
                        {ecart > 0 ? '+' : ''}{ecart} %
                      </span>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {data && (
        <>
          <button
            type="button"
            onClick={handleExportPdf}
            disabled={exporting}
            className="mt-3 w-full text-[10px] uppercase tracking-widest font-bold text-accent-light border border-accent/30 rounded-lg py-2 hover:bg-accent/10 transition-colors disabled:opacity-50"
          >
            {exporting ? 'Génération du PDF...' : 'Exporter en PDF'}
          </button>

          {exportError && (
            <p className="mt-2 text-[10px] text-red-400 font-bold bg-red-900/20 p-2 rounded border border-red-900/50">
              Erreur lors de l'export PDF : {exportError}
            </p>
          )}
        </>
      )}
    </div>
  );
}
