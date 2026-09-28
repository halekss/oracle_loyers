#!/usr/bin/env bash
# Scraping hebdomadaire, hors Airflow (Chrome fenêtré + undetected_chromedriver,
# impossible dans le conteneur). Lancé par le Planificateur de tâches Windows
# le lundi 20h via `wsl.exe -d Ubuntu -- <ce script>`, avant le DAG
# oracle_annonces_pipeline de 22h qui fusionne les CSV produits ici.
#
# Pour chaque ville de scraping_config.json : les scrapers de `sites_actifs`,
# puis complete_data_extraction (absent du DAG). Un scraper en échec
# n'arrête pas les autres ; le code de sortie signale s'il y en a eu un.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"
CONFIG="$ROOT/scripts/scraping_config.json"
LOG="$ROOT/scripts/logs/run_scrapers.log"
mkdir -p "$(dirname "$LOG")"

# Chrome s'affiche via WSLg : wsl.exe fournit normalement DISPLAY.
export DISPLAY="${DISPLAY:-:0}"

exec 9>"$ROOT/scripts/logs/run_scrapers.lock"
if ! flock -n 9; then
  echo "$(date '+%F %T') déjà en cours, abandon" >>"$LOG"
  exit 1
fi

log() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }

read -r -a VILLES <<<"$("$PY" -c "import json; print(' '.join(json.load(open('$CONFIG'))['villes']))")"
read -r -a SITES <<<"$("$PY" -c "import json; print(' '.join(json.load(open('$CONFIG'))['sites_actifs']))")"

echecs=0
log "=== Début : villes=${VILLES[*]} sites=${SITES[*]}"
for ville in "${VILLES[@]}"; do
  for site in "${SITES[@]}"; do
    script="scraper_${site/century21/century_21}.py"
    log "[$ville] $script"
    if ! (cd "$ROOT/scripts" && SCRAPING_VILLE="$ville" "$PY" "$script") >>"$LOG" 2>&1; then
      log "[$ville] ÉCHEC $script"
      echecs=$((echecs + 1))
    fi
  done
  log "[$ville] complete_data_extraction"
  if ! (cd "$ROOT/backend/scripts" && "$PY" complete_data_extraction.py --ville "$ville") >>"$LOG" 2>&1; then
    log "[$ville] ÉCHEC complete_data_extraction"
    echecs=$((echecs + 1))
  fi
done
log "=== Fin : $echecs échec(s)"
exit $((echecs > 0))
