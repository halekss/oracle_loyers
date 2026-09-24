// ORA-178/179 : ordre imposé des 8 vues du rail (maquette
// nav-b3v2-recherche), source unique partagée par PanelNav (rendu du rail)
// et App.jsx (résolution du contenu affiché par PanelSheet pour la vue
// active). "Recherche" (ORA-179) est passée en 2e position — juste après
// Accueil, avant Scan — désormais le seul point d'entrée pour lancer une
// recherche (la Topbar a été vidée de ses contrôles).
export const PANEL_VIEWS = [
  { id: 'accueil', label: 'Accueil' },
  { id: 'recherche', label: 'Recherche' },
  { id: 'scan', label: 'Scan' },
  { id: 'estimation', label: 'Estimation' },
  { id: 'calques', label: 'Calques' },
  { id: 'annonces', label: 'Annonces' },
  { id: 'fiche', label: 'Fiche' },
  { id: 'immotep', label: 'Immotep' },
];
