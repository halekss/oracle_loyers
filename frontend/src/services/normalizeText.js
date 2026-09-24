// ORA-176 : normalisation tolérante aux accents/casse, équivalente à
// `normalize_text` (backend/services/text_matching.py) — même approche
// (NFKD + suppression des marques combinantes + minuscules), pas un import
// direct (langages différents) mais un comportement délibérément aligné,
// pour que la palette de recherche filtre comme le ferait le backend
// (resolve_quartier_filter) sur la même saisie.
const COMBINING_MARKS_RE = /[̀-ͯ]/g;

export function normalizeText(value) {
  return String(value ?? '')
    .normalize('NFKD')
    .replace(COMBINING_MARKS_RE, '')
    .toLowerCase();
}
