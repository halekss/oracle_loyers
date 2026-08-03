import logging
import time

import requests

logger = logging.getLogger(__name__)

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


def request_with_retry(method, url, max_retries=3, backoff_seconds=2, timeout=30, **kwargs):
    """
    Requête HTTP avec timeout et retry/backoff sur les erreurs transitoires
    (exceptions réseau, codes 429/5xx), sur le modèle de la bascule
    multi-miroirs déjà en place dans api_overpass.py.

    Renvoie la Response en cas de succès (y compris un code d'erreur non
    transitoire, laissé à l'appelant), ou None si toutes les tentatives ont
    échoué pour une raison transitoire. Un échec définitif est loggé en
    ERROR mais ne lève jamais d'exception, pour ne pas interrompre le
    pipeline appelant.
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.request(method, url, timeout=timeout, **kwargs)
        except requests.exceptions.RequestException as exc:
            last_error = str(exc)
            logger.warning(
                "Tentative %s/%s échouée (%s) pour %s %s", attempt, max_retries, last_error, method, url
            )
        else:
            if response.status_code not in TRANSIENT_STATUS_CODES:
                return response
            last_error = f"HTTP {response.status_code}"
            logger.warning(
                "Tentative %s/%s échouée (%s) pour %s %s", attempt, max_retries, last_error, method, url
            )

        if attempt < max_retries:
            time.sleep(backoff_seconds * attempt)

    logger.error(
        "Échec définitif après %s tentatives pour %s %s : %s", max_retries, method, url, last_error
    )
    return None
