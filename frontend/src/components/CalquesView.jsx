import { useEffect, useState } from 'react';
import mapLayersConfig from '../config/mapLayers.config.json';
import { CAVALIER_STYLES, defaultExpandedCategory } from '../services/cavaliersDisplay';
import CavalierRow from './CavalierRow';
import LayerSwitch from './LayerSwitch';

// Codes de lignes (métro/funiculaire) affichés en méta des lignes "Fonds de
// carte" (maquette vue-calques.png) : faits géographiques statiques propres
// à Lyon, sans source dynamique dans l'app (aucun calque par ligne) — pas
// affichés pour une autre ville tant qu'ils ne sont pas vérifiés pour elle.
const LYON_LINE_CODES = { Metro: 'A B C D', Funicular: 'F1 F2' };

const quartiersLayer = mapLayersConfig.find((layer) => layer.key === 'Quartiers');

function FondDeCarteRow({ swatch, label, meta, checked, onToggle }) {
  return (
    <div className="flex items-center gap-2 min-h-[38px] py-1.5 border-b" style={{ borderColor: '#1C2440' }}>
      <div className="flex-1 flex items-center gap-2 min-w-0">
        {swatch}
        <span className="text-sm truncate" style={{ color: '#F1F5F9' }}>{label}</span>
        {meta && (
          <span className="text-[11px] ml-auto shrink-0 whitespace-nowrap" style={{ color: '#8B93A7' }}>{meta}</span>
        )}
      </div>
      <LayerSwitch checked={checked} onChange={onToggle} label={label} />
    </div>
  );
}

function Dot({ color }) {
  return <span className="shrink-0 w-3 h-3 rounded-full" style={{ background: color }} aria-hidden="true" />;
}

function DashedLine() {
  return (
    <span className="shrink-0 w-3 h-3 flex items-center justify-center" aria-hidden="true">
      <span className="w-3 border-t-2 border-dashed" style={{ borderColor: '#8B93A7' }} />
    </span>
  );
}

// Rayon des cavaliers : calculé en direct (GET /api/cavaliers,
// services/cavaliers_radius.py) pour 300/500/1000m — les 3 options sont
// actives.
const RADIUS_OPTIONS = [
  { label: '300 m', value: 300 },
  { label: '500 m', value: 500 },
  { label: '1 km', value: 1000 },
];

function RadiusSelector({ radiusM, onChange }) {
  return (
    <div className="flex items-center gap-1 shrink-0" role="group" aria-label="Rayon des cavaliers">
      {RADIUS_OPTIONS.map((option) => {
        const isActive = option.value === radiusM;
        return (
          <button
            key={option.label}
            type="button"
            aria-pressed={isActive}
            onClick={() => onChange(option.value)}
            className="px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wide focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#A78BFA]"
            style={{
              background: isActive ? '#7C3AED' : 'transparent',
              color: isActive ? '#F1F5F9' : '#8B93A7',
              cursor: 'pointer',
            }}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

function AnnonceColorSegment() {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm" style={{ color: '#F1F5F9' }}>Couleur des annonces</span>
      <div className="flex rounded-lg overflow-hidden border" style={{ borderColor: '#232B45' }}>
        <button
          type="button"
          aria-disabled="true"
          title="Bientôt"
          tabIndex={0}
          className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide"
          style={{ color: '#4B5266', cursor: 'not-allowed' }}
        >
          Écart
        </button>
        <button
          type="button"
          aria-pressed="true"
          className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide"
          style={{ background: '#7C3AED', color: '#F1F5F9' }}
        >
          Type
        </button>
      </div>
    </div>
  );
}

// Contenu de la vue "Calques" du rail (maquette vue-calques.png) : le bloc
// "Fonds de carte" pilote les calques transports/quartiers, et le bloc
// "Cavaliers" sert de lecture détaillée des 4 cavaliers autour du quartier
// scanné — mêmes données que le bloc "Les 4 Cavaliers" de la vue Scan
// (`cavaliersDetail`/`facteurs`, /api/quartier-stats), jamais recalculées ici.
export default function CalquesView({
  layers, onToggleLayer, cavaliersDetail, facteurs, isLoadingCavaliers,
  radiusM, onChangeRadiusM, quartier, zonesCount, ville, onGoToRecherche,
}) {
  const [expandedCategory, setExpandedCategory] = useState(() => defaultExpandedCategory(cavaliersDetail));

  // Nouveau scan (ou son absence) : la ligne dépliée par défaut redevient
  // celle qui compte le plus de lieux, jusqu'à ce que l'utilisateur en
  // déplie une autre lui-même.
  useEffect(() => {
    setExpandedCategory(defaultExpandedCategory(cavaliersDetail));
  }, [cavaliersDetail]);

  const hasCavaliersDetail = Boolean(cavaliersDetail && cavaliersDetail.length > 0);
  const lineCodes = ville === 'lyon' ? LYON_LINE_CODES : {};

  return (
    <div className="p-4 md:p-5 space-y-5">
      <div>
        <h3 className="text-[10px] uppercase tracking-widest font-bold mb-2" style={{ color: '#8B93A7' }}>
          Fonds de carte
        </h3>
        <div className="rounded-[14px] border overflow-hidden px-3" style={{ background: '#0F1630', borderColor: '#232B45' }}>
          <FondDeCarteRow
            swatch={<Dot color="#EF4444" />}
            label="Métro & stations"
            meta={lineCodes.Metro}
            checked={Boolean(layers.Metro)}
            onToggle={() => onToggleLayer('Metro')}
          />
          <FondDeCarteRow
            swatch={<DashedLine />}
            label="Funiculaires"
            meta={lineCodes.Funicular}
            checked={Boolean(layers.Funicular)}
            onToggle={() => onToggleLayer('Funicular')}
          />
          <FondDeCarteRow
            swatch={<Dot color={quartiersLayer?.uiColor || '#a78bfa'} />}
            label="€/m² par arrondissement"
            meta={zonesCount != null ? `${zonesCount} zones` : undefined}
            checked={Boolean(layers.Quartiers)}
            onToggle={() => onToggleLayer('Quartiers')}
          />
          <div className="flex items-center min-h-[38px] py-2">
            <AnnonceColorSegment />
          </div>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[10px] uppercase tracking-widest font-bold" style={{ color: '#8B93A7' }}>
            Cavaliers{quartier ? ` · ${quartier}` : ''}
          </h3>
          <RadiusSelector radiusM={radiusM} onChange={onChangeRadiusM} />
        </div>

        {!hasCavaliersDetail && (
          <div
            className="rounded-[14px] border px-4 py-4 mb-3 text-center"
            style={{ background: '#0F1630', borderColor: '#232B45' }}
          >
            <p className="text-xs mb-3" style={{ color: '#8B93A7' }}>
              Lance un scan pour voir les cavaliers d'un quartier.
            </p>
            <button
              type="button"
              onClick={onGoToRecherche}
              className="min-h-[44px] px-4 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-bold uppercase text-xs tracking-widest transition-colors"
            >
              Aller à Recherche
            </button>
          </div>
        )}

        <div className="rounded-[14px] border overflow-hidden px-3" style={{ background: '#0F1630', borderColor: '#232B45' }}>
          {CAVALIER_STYLES.map((style) => {
            const detail = cavaliersDetail?.find((cat) => cat.categorie === style.categorie);
            const phrase = facteurs?.find((f) => f.categorie === style.categorie)?.phrase;
            return (
              <CavalierRow
                key={style.categorie}
                categorie={style.categorie}
                color={style.color}
                shape={style.shape}
                detail={detail}
                phrase={phrase}
                isLoading={isLoadingCavaliers}
                isVisible={Boolean(layers[style.categorie])}
                onToggleVisibility={() => onToggleLayer(style.categorie)}
                isExpanded={expandedCategory === style.categorie}
                onToggleExpand={() => setExpandedCategory((prev) => (prev === style.categorie ? null : style.categorie))}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
