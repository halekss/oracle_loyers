import { Component } from 'react';

// Les Error Boundary React doivent être des composants classe : aucun
// équivalent à base de hooks n'existe pour intercepter les erreurs de rendu.
//
// ORA-123 : `fallback` (optionnel) permet d'isoler un panneau précis
// (carte, oracle, chat) plutôt que de faire planter tout l'écran — soit un
// élément statique, soit une fonction `(reset) => élément` pour offrir un
// "Réessayer" qui referme le boundary sans recharger toute la page. Sans
// `fallback`, comportement inchangé (plein écran, reload).
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error('Erreur de rendu capturée par ErrorBoundary:', error, info);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      const { fallback } = this.props;

      if (typeof fallback === 'function') {
        return fallback(this.handleReset);
      }
      if (fallback) {
        return fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center h-screen w-screen bg-slate-950 text-slate-200 gap-4 p-6 text-center">
          <h1 className="text-xl font-black tracking-tighter text-white">
            ORACLE <span className="text-purple-500">DES LOYERS</span>
          </h1>
          <p className="text-sm text-slate-400 max-w-md">
            Un problème d'affichage inattendu est survenu. Rechargez la page pour continuer.
          </p>
          <button
            type="button"
            onClick={this.handleReload}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-white text-sm font-semibold transition-colors"
          >
            Recharger la page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
