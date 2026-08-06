// Déclenche le téléchargement direct d'un blob (ORA-121 : export PDF sans
// passer par le sélecteur d'impression système).
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
