"""
Configuration centralisée de l'observabilité applicative du backend (ORA-63).

Deux responsabilités :
- `configure_logging()` : configure le logger racine avec un format
  structuré cohérent (timestamp, niveau, module d'origine) et un niveau
  configurable via la variable d'environnement `LOG_LEVEL` (`INFO` par
  défaut). Remplace les `print()` utilisés pour les erreurs applicatives.
- `init_sentry()` : initialise le SDK Sentry pour le tracking d'erreurs si
  `SENTRY_DSN` est renseigné. No-op silencieux sinon, pour ne jamais casser
  le dev local ou la CI où cette variable n'existe pas.

Ce module est importé et appelé par `app.py` au tout début du démarrage,
avant l'initialisation de Flask et le chargement des données/modèle.
"""
import logging
import os

# Même format que le logging structuré des scrapers (scripts/scraper_utils.py)
# pour rester cohérent entre les deux moitiés du projet.
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def configure_logging():
    """
    Configure le logger racine du process avec un format structuré et un
    niveau piloté par `LOG_LEVEL` (INFO par défaut, insensible à la casse).
    Une valeur invalide dans `LOG_LEVEL` retombe silencieusement sur INFO
    plutôt que de faire planter le démarrage du serveur.

    Idempotent : les appels suivants ne dupliquent pas les handlers (utile
    en tests, ou si le module est importé plusieurs fois dans le même
    process), ils se contentent de reprendre le niveau/format à jour.
    """
    global _configured

    level_name = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    level = logging.getLevelName(level_name)
    if not isinstance(level, int):
        level = logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    if not _configured:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        _configured = True
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)

    return root_logger


def init_sentry():
    """
    Initialise sentry-sdk pour capturer automatiquement les exceptions non
    gérées et les réponses 5xx (intégration Flask), uniquement si
    `SENTRY_DSN` est défini. Silencieusement no-op sinon (dev local/CI).

    Renvoie le module `sentry_sdk` si l'initialisation a eu lieu, `None`
    sinon.
    """
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return None

    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
    except ImportError:
        logging.getLogger(__name__).warning(
            "SENTRY_DSN est défini mais le paquet sentry-sdk n'est pas "
            "installé : tracking d'erreurs désactivé."
        )
        return None

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        # Pas de tracing de performance par défaut (payant en volume) :
        # seul le tracking d'erreurs nous intéresse ici. Ajustable via env.
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        send_default_pii=False,
    )
    logging.getLogger(__name__).info(
        "Sentry initialisé : tracking d'erreurs actif (environment=%s).",
        os.environ.get("SENTRY_ENVIRONMENT", "production"),
    )
    return sentry_sdk
