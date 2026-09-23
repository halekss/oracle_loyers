import React, { useState, useEffect } from "react";
import { api, describeApiError } from "../services/api";
import { downloadBlob } from "../services/downloadBlob";

const VILLE_LABELS = { lyon: { nom: 'Lyon', gentile: 'lyonnaises' }, lille: { nom: 'Lille', gentile: 'lilloises' } };
const SCENARIO_DELTAS = [-15, 0, 15];
const MIN_SCENARIO_SURFACE = 9;

const formatPrice = (p) => (p ? Math.round(p).toLocaleString('fr-FR') : "--");
const formatM2 = (p) => (p ? p.toLocaleString('fr-FR', { maximumFractionDigits: 1 }) : "--");

// `onViewAnnonces` (optionnel, ORA-127) : appelé avec le quartier scanné
// (`data.quartier`) quand l'utilisateur clique le lien direct vers ses
// annonces — le parent (App) s'en sert pour présélectionner AnnoncesList.
// `ville`/`health` (ORA-171) : alimentent "± N € (erreur moyenne du modèle
// XGBoost <Ville>)" et "entraîné sur N annonces" avec les vraies métriques
// du modèle actif plutôt que des chiffres codés en dur.
export default function ResultCard({ data, loading, priceHistory, onViewAnnonces, ville, health }) {

  const safeData = data || {};
  const stats = safeData.stats || {};

  const estimatedPrice = safeData.estimated_price || 0;
  const m2PriceRaw = stats.prix_m2 || 0;
  const confiance = safeData.confiance;
  const quartier = safeData.quartier;
  const facteurs = safeData.facteurs || [];
  const comparables = safeData.comparables || [];
  const surface = safeData.surface;
  // ORA-171 : le panneau "Estimation personnalisée" (maquette 03) ne
  // s'affiche que si une vraie prédiction XGBoost a eu lieu (surface +
  // type précis fournis) — sinon on garde l'affichage "moyenne du secteur"
  // existant (scan sans surface, périmètre ORA-167/epic ORA-162).
  const hasModelEstimate = Boolean(surface) && Boolean(confiance);

  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);
  const [scenarios, setScenarios] = useState(null);

  const confidenceStyles = {
    'Élevée': 'bg-green-900/40 text-green-400 border-green-700/50',
    'Moyenne': 'bg-amber-900/40 text-amber-400 border-amber-700/50',
    'Faible': 'bg-red-900/40 text-red-400 border-red-700/50',
  };

  // ORA-171 : "Et si la surface change ?" — 3 scénarios (surface -15/=/+15),
  // chacun une vraie prédiction du modèle (sauf la surface courante, déjà
  // disponible via `estimatedPrice`). Non bloquant : un scénario qui échoue
  // est simplement omis plutôt que de casser tout le panneau.
  useEffect(() => {
    if (!hasModelEstimate) {
      setScenarios(null);
      return;
    }
    let cancelled = false;
    const targets = [...new Set(SCENARIO_DELTAS.map((d) => Math.max(MIN_SCENARIO_SURFACE, Math.round(surface + d))))];

    Promise.all(
      targets.map((s) =>
        s === surface
          ? Promise.resolve({ surface: s, estimated_price: estimatedPrice })
          : api.predict({ surface: s, quartier, type_local: safeData.type })
              .then((r) => (typeof r.estimated_price === 'number' ? { surface: s, estimated_price: r.estimated_price } : null))
              .catch(() => null)
      ),
    ).then((results) => {
      if (!cancelled) setScenarios(results.filter(Boolean));
    });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasModelEstimate, surface, quartier, safeData.type]);

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
    const rangeLow = mae ? Math.max(0, Math.round(estimatedPrice - mae)) : null;
    const rangeHigh = mae ? Math.round(estimatedPrice + mae) : null;

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

        {/* Carte principale : estimation + prix/m² */}
        <div className="grid grid-cols-2 gap-3 bg-ink-900 border border-ink-700 rounded-xl p-4">
          <div>
            <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1">
              Estimation modèle · {surface} m²
            </p>
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-black text-white">{formatPrice(estimatedPrice)}</span>
              <span className="text-base text-slate-500">€</span>
            </div>
            {mae != null && (
              <p className="mt-1 text-[10px] text-slate-500">
                ± {formatPrice(mae)} € (erreur moyenne du modèle XGBoost {villeInfo.nom})
              </p>
            )}
          </div>
          <div className="text-right">
            <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1">Prix m²</p>
            <div className="text-xl font-black text-yellow-400">{formatM2(m2PriceRaw)} €</div>
            {safeData.quartierPrixM2 != null && (
              <p className="mt-1 text-[10px] text-slate-500">
                médiane {safeData.type} : {formatM2(safeData.quartierPrixM2)} €
              </p>
            )}
          </div>
          {rangeLow != null && rangeHigh != null && (
            <div className="col-span-2 mt-1">
              <div className="relative h-1.5 bg-ink-800 rounded-full">
                <div className="absolute inset-y-0 left-0 right-0 bg-violet-700/60 rounded-full" />
                <div
                  className="absolute -top-1 w-3.5 h-3.5 rounded-full bg-yellow-400 border-2 border-ink-900 -translate-x-1/2"
                  style={{ left: '50%' }}
                  title={`Estimation : ${formatPrice(estimatedPrice)} €`}
                />
              </div>
              <div className="flex justify-between mt-1 text-[9px] text-slate-500">
                <span>{formatPrice(rangeLow)} €</span>
                <span>{formatPrice(rangeHigh)} €</span>
              </div>
            </div>
          )}
        </div>

        {/* Et si la surface change ? */}
        {scenarios && scenarios.length > 1 && (
          <div className="mt-3">
            <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1.5">
              Et si la surface change ?
            </p>
            <div className="grid grid-cols-3 gap-2">
              {scenarios.map((s) => (
                <div
                  key={s.surface}
                  className={`rounded-lg p-2 text-center border ${
                    s.surface === surface ? 'bg-violet-900/30 border-violet-600' : 'bg-ink-900 border-ink-700'
                  }`}
                >
                  <p className="text-[10px] text-slate-500">{s.surface} m²</p>
                  <p className="text-sm font-black text-white">{formatPrice(s.estimated_price)} €</p>
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
        {comparables.length > 0 && (
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
              {comparables.map((c, i) => {
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
        <div className="flex-1 bg-gradient-to-br from-slate-800 to-slate-900 p-4 rounded-xl border border-purple-500/20 shadow-[0_4px_20px_rgba(0,0,0,0.2)] relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-2 opacity-5 text-6xl font-black text-white pointer-events-none">€</div>

          <div className="flex justify-between items-start">
            <div>
                <p className="text-[10px] uppercase text-purple-400 font-bold tracking-widest mb-1">Estimation Loyer</p>
                <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-black text-white tracking-tighter shadow-black drop-shadow-lg">
                    {formatPrice(estimatedPrice)}
                    </span>
                    <span className="text-lg text-slate-500">€</span>
                </div>
            </div>
            {confiance && (
              <span
                className={`text-[9px] uppercase font-bold tracking-wide px-2 py-1 rounded-full border ${confidenceStyles[confiance] || 'bg-slate-800 text-slate-400 border-slate-700'}`}
                title={safeData.count != null ? `Basée sur ${safeData.count} bien(s) comparable(s) du même quartier et type` : undefined}
              >
                Confiance IA : {confiance}
              </span>
            )}
          </div>
          {/* ORA-128 : explique la confiance plutôt que de la laisser abstraite */}
          {safeData.count != null && (
            <p className="mt-2 text-[9px] text-slate-500">
              Basée sur {safeData.count} bien{safeData.count > 1 ? 's' : ''} comparable{safeData.count > 1 ? 's' : ''} du même quartier et type.
            </p>
          )}
          {/* ORA-127 : lien direct depuis le quartier scanné vers ses annonces */}
          {quartier && onViewAnnonces && (
            <button
              type="button"
              onClick={() => onViewAnnonces(quartier)}
              className="mt-2 text-[9px] uppercase tracking-widest font-bold text-purple-400 hover:text-purple-300 transition-colors underline decoration-purple-500/40 underline-offset-2"
            >
              Voir les annonces de {quartier} →
            </button>
          )}
        </div>

        {/* PETIT BLOC : PRIX M2 */}
        <div className="w-1/3 bg-slate-900 p-3 rounded-xl border border-slate-700 flex flex-col justify-center items-center relative">
          <p className="text-[9px] uppercase text-slate-500 font-bold mb-1">Prix m²</p>
          <div className="text-xl font-bold text-yellow-400 font-mono">
            {formatPrice(m2PriceRaw)}
          </div>
          <p className="text-[9px] text-slate-600 mt-1">Moyenne</p>
        </div>
      </div>

      {comparables.length > 0 && (
        <div className="mt-3 bg-slate-900 rounded-xl border border-slate-700 p-3">
          <p className="text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-2">Biens comparables</p>
          <ul className="space-y-1">
            {comparables.map((c, i) => (
              <li key={i} className="flex justify-between text-[11px] text-slate-300">
                <span>{c.type_local || '—'}</span>
                <span>{formatPrice(c.prix)} € · {formatPrice(c.surface)} m²</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {data && (
        <>
          <button
            type="button"
            onClick={handleExportPdf}
            disabled={exporting}
            className="mt-3 w-full text-[10px] uppercase tracking-widest font-bold text-purple-400 border border-purple-500/30 rounded-lg py-2 hover:bg-purple-500/10 transition-colors disabled:opacity-50"
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
