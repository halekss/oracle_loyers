// Interrupteur de visibilité d'un calque — 38×22 px (maquette
// vue-calques.png), vrai bouton role="switch"/aria-checked (jamais un div
// cliquable), partagé par CavalierRow et les lignes "Fonds de carte" de la
// vue Calques.
export default function LayerSwitch({ checked, onChange, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={onChange}
      className="relative shrink-0 w-[38px] h-[22px] rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#A78BFA]"
      style={{ background: checked ? '#7C3AED' : '#232B45', boxShadow: checked ? '0 0 10px rgba(124,58,237,.5)' : 'none' }}
    >
      <span
        className="absolute top-[2px] left-[2px] w-[18px] h-[18px] rounded-full bg-white transition-transform duration-200"
        style={{ transform: checked ? 'translateX(16px)' : 'translateX(0)' }}
      />
    </button>
  );
}
