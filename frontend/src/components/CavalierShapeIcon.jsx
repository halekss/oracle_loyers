// Formes décoratives (aria-hidden) des 4 cavaliers — la couleur seule ne
// porte jamais l'information : le nom est toujours écrit en texte à côté
// (CavalierRow, légende carte "Cavaliers affichés").
const SHAPES = {
  circle: (color) => <circle cx="6" cy="6" r="5" fill={color} />,
  diamond: (color) => <polygon points="6,0 12,6 6,12 0,6" fill={color} />,
  triangle: (color) => <polygon points="6,1 11,11 1,11" fill={color} />,
  square: (color) => <rect x="1" y="1" width="10" height="10" fill={color} />,
};

export default function CavalierShapeIcon({ shape, color, className = '' }) {
  const render = SHAPES[shape] || SHAPES.circle;
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" className={`shrink-0 ${className}`}>
      {render(color)}
    </svg>
  );
}
