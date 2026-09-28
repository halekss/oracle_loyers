import { useState } from 'react';
import { sanitizeListingUrl } from '../services/sanitizeUrl';
import { getTypeCategory } from '../services/annonceType';

const ILLUSTRATION_BY_CATEGORY = {
  'Studio/T1': 'from-sky-900/50 to-slate-900 text-sky-400',
  'T2': 'from-emerald-900/50 to-slate-900 text-emerald-400',
  'T3': 'from-amber-900/50 to-slate-900 text-amber-400',
  'Grand (T4+)': 'from-rose-900/50 to-slate-900 text-rose-400',
};
const DEFAULT_ILLUSTRATION_CLASSES = 'from-slate-800 to-slate-900 text-slate-500';

// Photo de l'annonce en hotlink (URL du site source, jamais téléchargée ni
// re-servie — décision légale ORA-94/ORA-134/ORA-196, cf. LEGAL_DECISIONS.md).
// Repli sur l'illustration générique (icône SVG maison + type) sans photo,
// avec une URL non http(s), ou si l'image ne charge pas — jamais d'image
// cassée à l'écran. Extrait de AnnonceCard.jsx (ORA-196) pour être réutilisé
// tel quel par AnnonceDetailContent.jsx (fiche annonce, panneau droit).
// `className` : dimensions/ratio (défaut : vignette de carte, `h-20`) —
// passer `aspect-video w-full` pour le format 16:9 de la fiche.
// `rounded` : classes d'arrondi appliquées à la photo ET au repli, pour que
// les deux s'intègrent identiquement au conteneur appelant.
// `alt` : vide par défaut (décoratif, le titre est déjà affiché en texte à
// côté) — passer un texte descriptif quand l'image est le seul contexte
// visuel disponible (fiche annonce, sans titre affiché juste à côté).
export default function AnnonceIllustration({ titre, surface, image, alt = '', className = 'h-20', rounded = '' }) {
  const [broken, setBroken] = useState(false);
  const category = getTypeCategory(titre, surface);
  const classes = ILLUSTRATION_BY_CATEGORY[category] || DEFAULT_ILLUSTRATION_CLASSES;
  const photo = broken ? null : sanitizeListingUrl(image);

  if (photo) {
    return (
      <div className={`relative bg-slate-900 ${className} ${rounded}`}>
        <img
          src={photo}
          alt={alt}
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={() => setBroken(true)}
          className={`w-full h-full object-cover ${rounded}`}
        />
        {category && (
          <span className="absolute bottom-1 left-1 text-[8px] uppercase tracking-widest font-bold px-1.5 py-0.5 rounded bg-slate-900/75 text-white">
            {category}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={`flex flex-col items-center justify-center gap-1 bg-gradient-to-br ${classes} ${className} ${rounded}`}>
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-7 h-7"
        aria-hidden="true"
      >
        <path d="M3 11.5 12 4l9 7.5" />
        <path d="M5.5 10v9.5h13V10" />
        <path d="M10 19.5v-6h4v6" />
      </svg>
      {category && (
        <span className="text-[8px] uppercase tracking-widest font-bold opacity-80">{category}</span>
      )}
    </div>
  );
}
