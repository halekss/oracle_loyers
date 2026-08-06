import html as html_module
from datetime import datetime

try:
    # WeasyPrint dépend de libs système (libpango/libcairo/libgdk-pixbuf,
    # voir Dockerfile) absentes de certains environnements de dev (ex: macOS
    # sans Homebrew) — import optionnel, comme le modèle XGBoost dans app.py,
    # pour ne pas faire planter tout le reste de l'app à l'import.
    from weasyprint import HTML
except Exception:
    HTML = None

# Charte sombre/violette de l'app (cf. frontend/tailwind.config.js), reprise
# ici pour un rapport visuellement cohérent avec ResultCard.jsx (ORA-121).
BACKGROUND = "#0f172a"
SURFACE = "#1e293b"
BORDER = "#334155"
TEXT = "#f8fafc"
MUTED = "#94a3b8"
ACCENT = "#a78bfa"


def _escape(value):
    return html_module.escape(str(value or ""))


def _format_price(value):
    if value is None:
        return "--"
    return f"{round(float(value)):,}".replace(",", " ")


def _format_date(iso_value):
    try:
        return datetime.fromisoformat(str(iso_value)).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return _escape(iso_value)


def build_report_html(data):
    """Construit le HTML source du rapport PDF (fonction pure, testable
    indépendamment du rendu WeasyPrint). `data` reprend le résultat déjà
    affiché par ResultCard.jsx : quartier, estimated_price, prix_m2,
    confiance, count, type_local, facteurs."""
    quartier = _escape(data.get("quartier"))
    estimated_price = _format_price(data.get("estimated_price"))
    prix_m2 = _format_price(data.get("prix_m2"))
    confiance = _escape(data.get("confiance")) if data.get("confiance") else None
    type_local = _escape(data.get("type_local")) if data.get("type_local") else None
    count = data.get("count")
    facteurs = data.get("facteurs") or []
    historique = data.get("historique") or []
    comparables = data.get("comparables") or []

    meta_parts = [f"Quartier : {quartier}"]
    if type_local:
        meta_parts.append(f"Type : {type_local}")
    if count is not None:
        meta_parts.append(f"{int(count)} bien(s) comparé(s)")
    meta_line = " · ".join(meta_parts)

    confiance_html = (
        f'<span class="badge">Confiance IA : {confiance}</span>' if confiance else ""
    )

    facteurs_html = ""
    if facteurs:
        items = "".join(
            f'<li><strong>{_escape(f.get("categorie"))}</strong> — {_escape(f.get("phrase"))}</li>'
            for f in facteurs
        )
        facteurs_html = f"""
        <h2>Les 4 Cavaliers du quartier</h2>
        <ul class="facteurs">{items}</ul>
        """

    historique_html = ""
    if historique:
        rows = "".join(
            f"<tr><td>{_format_date(point.get('date'))}</td>"
            f"<td>{_format_price(point.get('prix_m2_moyen'))} €/m²</td>"
            f"<td>{_escape(point.get('count'))} bien(s)</td></tr>"
            for point in historique
        )
        historique_html = f"""
        <h2>Historique du prix moyen/m²</h2>
        <table class="data-table">{rows}</table>
        """

    comparables_html = ""
    if comparables:
        rows = "".join(
            f"<tr><td>{_escape(c.get('type_local')) or '—'}</td>"
            f"<td>{_format_price(c.get('prix'))} €</td>"
            f"<td>{_format_price(c.get('surface'))} m²</td></tr>"
            for c in comparables
        )
        comparables_html = f"""
        <h2>Biens comparables</h2>
        <table class="data-table">{rows}</table>
        """

    return f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        @page {{ size: A4; margin: 2cm; }}
        body {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            background: {BACKGROUND};
            color: {TEXT};
            margin: 0;
            padding: 0;
        }}
        h1 {{
            font-size: 22px;
            font-weight: 900;
            margin: 0 0 4px 0;
            color: {TEXT};
        }}
        .subtitle {{
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {ACCENT};
            font-weight: 700;
            margin-bottom: 20px;
        }}
        .meta {{
            font-size: 11px;
            color: {MUTED};
            margin-bottom: 16px;
        }}
        .price-block {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 20px;
        }}
        .price-label {{
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {ACCENT};
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .price-value {{
            font-size: 32px;
            font-weight: 900;
        }}
        .price-m2 {{
            font-size: 12px;
            color: {MUTED};
            margin-top: 4px;
        }}
        .badge {{
            display: inline-block;
            font-size: 9px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 999px;
            border: 1px solid {ACCENT};
            color: {ACCENT};
            margin-top: 8px;
        }}
        h2 {{
            font-size: 14px;
            font-weight: 700;
            margin: 20px 0 8px 0;
            color: {TEXT};
        }}
        ul.facteurs {{
            list-style: disc;
            padding-left: 18px;
            margin: 0;
            font-size: 11px;
            color: {TEXT};
        }}
        ul.facteurs li {{
            margin-bottom: 6px;
        }}
        table.data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            color: {TEXT};
        }}
        table.data-table td {{
            padding: 4px 6px;
            border-bottom: 1px solid {BORDER};
        }}
        .disclaimer {{
            font-size: 9px;
            color: {MUTED};
            margin-top: 30px;
        }}
    </style>
    </head>
    <body>
        <h1>Oracle des Loyers</h1>
        <p class="subtitle">Rapport d'estimation</p>
        <p class="meta">{meta_line}</p>

        <div class="price-block">
            <p class="price-label">Estimation loyer</p>
            <p class="price-value">{estimated_price} €</p>
            <p class="price-m2">Prix moyen au m² : {prix_m2} €</p>
            {confiance_html}
        </div>

        {facteurs_html}

        {historique_html}

        {comparables_html}

        <p class="disclaimer">Estimation générée par l'Oracle des Loyers, à titre indicatif — non contractuelle.</p>
    </body>
    </html>
    """


def render_estimation_pdf(data):
    """Rend le rapport d'estimation en PDF (bytes), via WeasyPrint (ORA-121)."""
    if HTML is None:
        raise RuntimeError(
            "WeasyPrint indisponible : dépendances système manquantes "
            "(libpango/libcairo/libgdk-pixbuf, voir Dockerfile)"
        )
    return HTML(string=build_report_html(data)).write_pdf()
