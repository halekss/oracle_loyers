import React from "react";

// ORA-72 : évolution du prix moyen/m² par quartier à travers les snapshots
// de données disponibles (backend/data/snapshots/). Tant qu'il n'y a pas
// assez d'historique (un seul snapshot enregistré), le backend renvoie
// status="insufficient_history" plutôt qu'une fausse tendance à un point —
// affiché honnêtement ici plutôt que masqué.
//
// ORA-129 : le `message` renvoyé par le backend dans ce cas indique aussi à
// l'utilisateur·rice quand s'attendre à de nouvelles données ("généralement
// chaque semaine"), sans transformer la cadence visée du pipeline (DAG
// Airflow hebdomadaire, non surveillé pour les runs manqués) en promesse
// ferme — voir README section "Versioning des snapshots de données".
export default function PriceHistory({ status, message, historique }) {
  if (!status) return null;

  return (
    <div className="print:hidden">
      <p className="text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-1.5">
        Évolution du prix moyen/m²
      </p>

      {status === "insufficient_history" ? (
        <p className="text-[11px] text-slate-500 italic">{message}</p>
      ) : (
        <table className="w-full text-[11px] text-slate-400">
          <thead>
            <tr className="text-slate-500 uppercase text-[9px]">
              <th className="text-left font-bold pb-1">Date</th>
              <th className="text-right font-bold pb-1">Prix/m²</th>
              <th className="text-right font-bold pb-1">Biens</th>
            </tr>
          </thead>
          <tbody>
            {historique.map((point) => (
              <tr key={point.date} className="border-t border-slate-800/50">
                <td className="py-1">{new Date(point.date).toLocaleDateString('fr-FR')}</td>
                <td className="text-right py-1 font-mono text-yellow-400">{Math.round(point.prix_m2_moyen)} €</td>
                <td className="text-right py-1">{point.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
