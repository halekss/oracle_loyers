// ORA-178 : ordre imposé des 8 vues du rail (maquette nav-b3-classeur),
// source unique partagée par PanelNav (rendu du rail) et App.jsx (résolution
// du contenu affiché par PanelSheet pour la vue active).
export const PANEL_VIEWS = [
  { id: 'accueil', label: 'Accueil' },
  { id: 'scan', label: 'Scan' },
  { id: 'estimation', label: 'Estimation' },
  { id: 'calques', label: 'Calques' },
  { id: 'annonces', label: 'Annonces' },
  { id: 'fiche', label: 'Fiche' },
  { id: 'immotep', label: 'Immotep' },
  { id: 'recherche', label: 'Recherche' },
];
