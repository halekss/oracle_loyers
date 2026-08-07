"""
Vérification HTTP asynchrone des annonces à statut incertain (ORA-134 bis,
tier 2 du nettoyage non-destructif — complète la fusion préservante de
clean_immo.py, Task 2). Contrairement à prune_dead_annonces.py/
prune_dead_map_listings.py (ORA-134, suppression physique), ce script ne
supprime jamais de ligne : il met uniquement à jour la colonne `statut`.

Cible : les annonces de master_immo_final.csv dont le statut est
`a_verifier`, ou `active` mais dont `derniere_verification_http` dépasse
`ttl_days` (re-vérification périodique même d'une annonce jugée active, pour
détecter une disparition qui ne serait pas encore passée par la fusion
diff-scrape de clean_immo.py).

aiohttp + asyncio.Semaphore pour un rate limiting raisonnable (concurrence
plafonnée, pas de rafale sur les sites sources) — remplace le
`time.sleep(random.uniform(...))` séquentiel des scripts ORA-134 par un
throttling concurrent équivalent en esprit mais bien plus rapide sur le
volume total.

Met à jour master_immo_final.csv (source de vérité du statut, atomique) puis
synchronise annonces.db (consommé par /api/annonces) pour le même run — pas
besoin d'attendre le pipeline hebdomadaire pour que l'API reflète le
nettoyage quotidien.

Usage :
    python backend/scripts/verify_annonces_async.py [--dry-run] [--concurrency N] [--ttl-days N]
"""
import argparse
import asyncio
import logging
import os
import random
import sys

import aiohttp
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from scripts.prune_dead_annonces import looks_like_soft_404, REQUEST_HEADERS  # noqa: E402
from services import annonces_store  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MASTER_CSV_PATH = os.path.join(backend_dir, "data", "master_immo_final.csv")
ANNONCES_DB_PATH = annonces_store.DEFAULT_DB_PATH

DEFAULT_CONCURRENCY = 5
DEFAULT_TTL_DAYS = 15
DEFAULT_TIMEOUT_SECONDS = 10
DEAD_STATUS_CODES = {404, 410}


async def check_url_status_async(url, session, timeout=DEFAULT_TIMEOUT_SECONDS):
    """Version asynchrone de check_url_status (prune_dead_annonces.py) : même
    contrat (True=mort, False=vivant, None=ambigu), même détection soft-404
    (looks_like_soft_404, réutilisée telle quelle — une seule source de vérité
    pour les patterns de contenu 'annonce supprimée' entre les tiers sync et async)."""
    try:
        async with session.get(
            url, headers=REQUEST_HEADERS, timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True,
        ) as response:
            if response.status in DEAD_STATUS_CODES:
                return True
            if response.status == 200:
                text = await response.text()
                if looks_like_soft_404(text):
                    return True
                return False
            logger.warning("Statut ambigu pour %s (HTTP %s) : conservée par prudence.", url, response.status)
            return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.warning("Erreur réseau pour %s (%s) : conservée par prudence.", url, exc)
        return None


def _rows_to_verify(df, ttl_days, reference_date=None):
    """Sélectionne les lignes à vérifier : statut a_verifier, ou active avec
    derniere_verification_http absente/dépassant ttl_days.

    Exclut aussi toute ligne dont `url` n'est pas une chaîne non vide
    (Finding 4) : une url NaN/malformée provoque un TypeError dans
    check_url_status_async (`aiohttp` construit une requête à partir de
    l'url), qui n'est pas un cas couvert par le contrat True/False/None du
    checker. Même garde que `step_sync_annonces_store` dans clean_immo.py
    (`if not isinstance(url, str): skip`), qui rencontre déjà ce genre de
    ligne malformée en pratique."""
    reference_date = reference_date or pd.Timestamp.now(tz='UTC')
    if 'derniere_verification_http' in df.columns:
        derniere_verif = pd.to_datetime(df['derniere_verification_http'], errors='coerce', utc=True)
        age_jours = (reference_date - derniere_verif).dt.days
        active_stale = (df['statut'] == 'active') & (age_jours.isna() | (age_jours > ttl_days))
    else:
        active_stale = df['statut'] == 'active'
    url_valide = df['url'].apply(lambda u: isinstance(u, str) and bool(u.strip()))
    return df[((df['statut'] == 'a_verifier') | active_stale) & url_valide].index


async def verify_annonces(
    csv_path=MASTER_CSV_PATH,
    db_path=ANNONCES_DB_PATH,
    concurrency=DEFAULT_CONCURRENCY,
    ttl_days=DEFAULT_TTL_DAYS,
    dry_run=False,
    checker=check_url_status_async,
):
    """Vérifie les annonces éligibles (cf. `_rows_to_verify`) et met à jour leur
    `statut` dans master_immo_final.csv (jamais de suppression de ligne) puis
    dans annonces.db. Renvoie les compteurs de la passe."""
    df = pd.read_csv(csv_path)
    if 'statut' not in df.columns:
        df['statut'] = 'active'
    if 'derniere_verification_http' not in df.columns:
        df['derniere_verification_http'] = ''

    to_check = _rows_to_verify(df, ttl_days)
    logger.info("%s annonce(s) éligible(s) à la vérification HTTP.", len(to_check))

    stats = {"checked": 0, "confirmed_dead": 0, "reconfirmed_alive": 0, "still_ambiguous": 0}
    semaphore = asyncio.Semaphore(concurrency)
    now_iso = pd.Timestamp.now(tz='UTC').isoformat()

    async def _check_one(idx, url):
        async with semaphore:
            await asyncio.sleep(random.uniform(0.1, 0.3))  # jitter, évite une rafale synchronisée
            try:
                status = await checker(url, session)
            except Exception as exc:
                # Défense en profondeur (Finding 4) : une ligne inattendue (url
                # malformée passée entre les mailles de _rows_to_verify, ou
                # toute autre exception imprévue du checker) ne doit jamais
                # faire échouer tout le batch via asyncio.gather -- traitée
                # comme un résultat ambigu (None), au même titre qu'un 403/5xx.
                logger.warning("Erreur inattendue pour %s (%s) : conservée par prudence.", url, exc)
                status = None
            return idx, status

    async with aiohttp.ClientSession() as session:
        tasks = [_check_one(idx, df.at[idx, 'url']) for idx in to_check]
        results = await asyncio.gather(*tasks)

    for idx, status in results:
        stats["checked"] += 1
        if status is True:
            df.at[idx, 'statut'] = 'inactive'
            df.at[idx, 'derniere_verification_http'] = now_iso
            stats["confirmed_dead"] += 1
            logger.info("Confirmée morte : %s", df.at[idx, 'url'])
        elif status is False:
            df.at[idx, 'statut'] = 'active'
            df.at[idx, 'derniere_verification_http'] = now_iso
            stats["reconfirmed_alive"] += 1
        else:
            # Finding 3 : résultat ambigu (403/5xx/timeout/exception imprévue) —
            # on ne sait PAS si l'annonce est vivante ou morte, donc on ne
            # touche pas derniere_verification_http. Le stamper à now_iso ici
            # enregistrerait un "on ne sait pas" comme "vérifié à l'instant",
            # ce qui suspendrait toute re-vérification d'une ligne active-stale
            # pendant tout ttl_days sur la foi d'un seul essai raté -- le cas
            # dominant, pas un cas limite, vu le taux de blocage anti-bot
            # attendu sur SeLoger.
            stats["still_ambiguous"] += 1

    logger.info(
        "Terminé : %s vérifiées, %s confirmées mortes, %s re-confirmées vivantes, %s toujours ambiguës.",
        stats["checked"], stats["confirmed_dead"], stats["reconfirmed_alive"],
        stats["still_ambiguous"],
    )

    if not dry_run and len(to_check) > 0:
        tmp_path = f"{csv_path}.tmp"
        df.to_csv(tmp_path, index=False)
        os.replace(tmp_path, csv_path)

        for idx, status in results:
            if status is None:
                continue
            annonces_store.update_statut(
                url=df.at[idx, 'url'],
                statut=df.at[idx, 'statut'],
                derniere_verification=df.at[idx, 'derniere_verification_http'],
                db_path=db_path,
            )

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Vérifie et logue sans rien modifier.")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Requêtes HTTP simultanées max.")
    parser.add_argument("--ttl-days", type=int, default=DEFAULT_TTL_DAYS, help="Âge max avant re-vérification d'une annonce active.")
    args = parser.parse_args()
    asyncio.run(verify_annonces(dry_run=args.dry_run, concurrency=args.concurrency, ttl_days=args.ttl_days))
