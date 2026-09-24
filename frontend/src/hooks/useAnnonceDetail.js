import { useEffect, useState } from 'react';
import { api, describeApiError } from '../services/api';
import { sanitizeListingUrl } from '../services/sanitizeUrl';
import { deriveSource } from '../services/annonceType';
import { downloadBlob } from '../services/downloadBlob';
import { useFavorites } from './useFavorites';

// ORA-178 : extrait de AnnonceDetailModal.jsx (fetch, export PDF, favori,
// redirection) — logique pure réutilisée à la fois par la modale (existante,
// AnnonceCard "Détails" sans rail) et la vue "Fiche" du panneau (rail),
// pour ne jamais dupliquer le fetch ni l'appel /api/report/pdf.
export function useAnnonceDetail(annonceId) {
  const [annonce, setAnnonce] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);
  const { isFavorite, toggleFavorite } = useFavorites();

  useEffect(() => {
    if (annonceId == null) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setAnnonce(null);

    api.getAnnonceDetail(annonceId)
      .then((data) => {
        if (!cancelled) setAnnonce(data);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error(err);
        setError(describeApiError(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [annonceId]);

  const safeUrl = sanitizeListingUrl(annonce?.url);
  const source = deriveSource(annonce?.url);
  const favorite = annonceId != null && isFavorite(annonceId);

  const handleVoirAnnonce = () => {
    api.logAnnonceClick(annonceId).catch((err) => {
      console.error('❌ Erreur tracking clic annonce:', err);
    });
    if (safeUrl) {
      window.open(safeUrl, '_blank', 'noopener,noreferrer');
    }
  };

  // ORA-174 : réutilise le générateur PDF existant (/api/report/pdf, ORA-121)
  // — pas de nouvel endpoint pour une fiche annonce, dont les champs
  // recouvrent ceux déjà acceptés (quartier/estimation/prix_m2/facteurs).
  const handleExportPdf = async () => {
    setExporting(true);
    setExportError(null);
    try {
      const facteurs = (annonce?.cavaliers_detail || [])
        .filter((cat) => cat.items.length > 0)
        .map((cat) => ({
          categorie: cat.categorie,
          phrase: `${cat.items[0].poi} à ${cat.items[0].dist_m} m (${cat.total} lieu${cat.total > 1 ? 'x' : ''} dans le rayon).`,
        }));
      const blob = await api.exportEstimationPdf({
        quartier: annonce.quartier,
        estimated_price: annonce.prix,
        prix_m2: annonce.prix_m2,
        type_local: annonce.type_local,
        facteurs,
      });
      const slug = (annonce.quartier || 'annonce').toLowerCase().replace(/[^a-z0-9]+/g, '-');
      downloadBlob(blob, `annonce-oracle-${slug}.pdf`);
    } catch (err) {
      console.error(err);
      setExportError(describeApiError(err));
    } finally {
      setExporting(false);
    }
  };

  const prixM2 = annonce?.prix_m2 ?? (annonce?.prix && annonce?.surface ? annonce.prix / annonce.surface : null);
  const ecart =
    prixM2 != null && annonce?.quartier_prix_m2_moyen
      ? Math.round(((prixM2 - annonce.quartier_prix_m2_moyen) / annonce.quartier_prix_m2_moyen) * 100)
      : null;

  return {
    annonce, loading, error, exporting, exportError,
    safeUrl, source, favorite, prixM2, ecart,
    toggleFavorite: () => toggleFavorite(annonceId),
    handleVoirAnnonce, handleExportPdf,
  };
}
