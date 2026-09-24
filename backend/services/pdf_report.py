import html as html_module
import statistics

try:
    # WeasyPrint dépend de libs système (libpango/libcairo/libgdk-pixbuf,
    # voir Dockerfile) absentes de certains environnements de dev (ex: macOS
    # sans Homebrew) — import optionnel, comme le modèle XGBoost dans app.py,
    # pour ne pas faire planter tout le reste de l'app à l'import.
    from weasyprint import HTML
except Exception:
    HTML = None

# ORA-177 : palette claire d'impression (maquette 09, `project/09-pdf.dc.html`)
# — volontairement différente de la charte sombre de l'app (encre économisée
# à l'impression, lisibilité papier), reprise depuis les styles calculés de
# la maquette Claude Design plutôt que devinée.
INK = "#0f172a"       # slate-900 : texte principal
MUTED = "#64748b"     # slate-500 : texte secondaire
FAINT = "#94a3b8"     # slate-400 : texte tertiaire (footer)
VIOLET = "#6d28d9"    # violet-700 : marque + accents
VIOLET_SOFT = "#faf5ff"  # violet-50 : fond des cases metriques
BORDER = "#e2e8f0"    # slate-200
GREEN = "#15803d"     # green-700 : écart négatif (moins cher que le marché)
AMBER = "#a16207"     # amber-700 : écart positif (plus cher que le marché)

SOURCES_LABEL = "Vizzit, PAP, ParuVendu, SeLoger, Orpi, Century 21"

TYPE_LABELS = {
    "T1": "T1", "Studio/T1": "un studio/T1", "Studio": "un studio",
    "T2": "T2", "T3": "T3", "T4+": "T4+", "Grand (T4+)": "un grand logement",
}


def _escape(value):
    return html_module.escape(str(value or ""))


def _format_price(value):
    if value is None:
        return "--"
    return f"{round(float(value)):,}".replace(",", " ")


def _format_m2(value):
    if value is None:
        return "--"
    return f"{float(value):,.1f}".replace(",", " ").replace(".", ",")


def _title_sentence(type_local, quartier):
    label = TYPE_LABELS.get(type_local, type_local) if type_local and type_local != "Tout" else None
    if label:
        article = "un" if not label.startswith("un") else ""
        prefix = f"{article} {label}".strip() if article else label
        return f"Ce que vaut {prefix} à {quartier}"
    return f"Ce que vaut un bien à {quartier}"


def _quartile_stats(values):
    """Médiane + P25/P75 d'une liste de prix (biens comparables). Renvoie
    (median, p25, p75) — p25/p75 sont None avec moins de 4 points (quartiles
    peu fiables sur un échantillon trop petit, pas d'affichage trompeur)."""
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return None, None, None
    median = statistics.median(clean)
    if len(clean) < 4:
        return median, None, None
    p25, _, p75 = statistics.quantiles(clean, n=4, method="inclusive")
    return median, p25, p75


def _ecart_pct(value, reference):
    if value is None or not reference:
        return None
    return round(((value - reference) / reference) * 100)


def _ecart_html(pct):
    if pct is None:
        return f'<span style="color:{MUTED}">—</span>'
    color = GREEN if pct < 0 else (AMBER if pct > 0 else MUTED)
    sign = "+" if pct > 0 else ""
    return f'<span style="color:{color};font-weight:700">{sign}{pct} %</span>'


def build_report_html(data):
    """Construit le HTML source du rapport PDF (fonction pure, testable
    indépendamment du rendu WeasyPrint), aligné sur la maquette Claude Design
    09 (`project/09-pdf.dc.html`, ORA-177). `data` reprend le résultat déjà
    affiché par ResultCard.jsx : quartier, estimated_price, prix_m2,
    confiance, count, type_local, surface, facteurs, comparables."""
    quartier = _escape(data.get("quartier"))
    type_local = data.get("type_local")
    estimated_price = data.get("estimated_price")
    payload_prix_m2 = data.get("prix_m2")
    count = data.get("count")
    surface = data.get("surface")
    data_as_of = data.get("data_as_of")
    facteurs = data.get("facteurs") or []
    comparables = data.get("comparables") or []

    breadcrumb_parts = [p for p in [quartier, _escape(type_local) if type_local and type_local != "Tout" else None] if p]
    breadcrumb = " · ".join(breadcrumb_parts).upper()
    title = _escape(_title_sentence(type_local, data.get("quartier")))

    # ORA-177 : loyer médian + P25/P75 dérivés des biens comparables reçus
    # (échantillon déjà représentatif, cf. app.py get_quartier_stats) —
    # aucune nouvelle statistique côté serveur, juste une lecture différente
    # d'une donnée déjà transmise. Repli sur l'estimation si aucun comparable.
    prices = [c.get("prix") for c in comparables]
    loyer_median, p25, p75 = _quartile_stats(prices)
    if loyer_median is None:
        loyer_median = estimated_price

    m2_values = [
        (c["prix"] / c["surface"]) for c in comparables
        if c.get("prix") and c.get("surface")
    ]
    prix_m2_median = statistics.median(m2_values) if m2_values else payload_prix_m2

    loyer_sub_parts = []
    if p25 is not None and p75 is not None:
        loyer_sub_parts.append(f"P25–P75 : {_format_price(p25)} – {_format_price(p75)} €")
    if count is not None:
        loyer_sub_parts.append(f"{int(count)} annonce{'s' if count > 1 else ''}")
    loyer_sub = " · ".join(loyer_sub_parts)

    estimation_box_html = ""
    if surface and estimated_price is not None:
        estimation_box_html = f"""
        <div class="metric-box">
            <p class="metric-label">Estimation {_format_price(surface)} m²</p>
            <p class="metric-value">{_format_price(estimated_price)} €</p>
            <p class="metric-sub">Estimation du modèle XGBoost.</p>
        </div>
        """

    cavaliers_html = ""
    if facteurs:
        items = "".join(
            f"""
            <div class="cavalier">
                <p class="cavalier-label">{_escape(f.get('categorie'))}</p>
                <p class="cavalier-phrase">{_escape(f.get('phrase'))}</p>
            </div>
            """
            for f in facteurs
        )
        cavaliers_html = f"""
        <p class="section-title">Les 4 cavaliers · 500 m</p>
        <div class="cavaliers-grid">{items}</div>
        """

    comparables_html = ""
    if comparables:
        sorted_rows = sorted(comparables, key=lambda c: c.get("prix") or 0)
        rows = ""
        for c in sorted_rows:
            prix = c.get("prix")
            surf = c.get("surface")
            m2 = (prix / surf) if prix and surf else None
            ecart = _ecart_pct(m2, prix_m2_median)
            rows += f"""
            <tr>
                <td>{_format_price(prix)} €</td>
                <td>{_format_price(surf)} m²</td>
                <td>{_format_m2(m2)} €</td>
                <td>{_escape(c.get('site')) or '—'}</td>
                <td class="num">{_ecart_html(ecart)}</td>
            </tr>
            """
        comparables_html = f"""
        <p class="section-title">Les {len(comparables)} annonces comparables</p>
        <table class="data-table">
            <thead>
                <tr><th>Loyer</th><th>Surface</th><th>€/m²</th><th>Source</th><th class="num">Écart €/m²</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        """

    meta_html = '<p class="meta-title">Rapport d\'estimation</p>'
    if data_as_of:
        meta_html += f'<p class="meta-date">Données au {_escape(data_as_of)}</p>'

    return f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        @page {{ size: A4; margin: 1.6cm; }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            background: #ffffff;
            color: {INK};
            margin: 0;
            padding: 0;
            font-size: 12px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid {VIOLET};
            padding-bottom: 10px;
            margin-bottom: 14px;
        }}
        .brand {{
            font-size: 20px;
            font-weight: 900;
            letter-spacing: 0.01em;
        }}
        .brand span {{ color: {VIOLET}; }}
        .meta-title {{
            font-size: 11px;
            font-weight: 800;
            text-align: right;
            margin: 0;
        }}
        .meta-date {{
            font-size: 10px;
            color: {MUTED};
            text-align: right;
            margin: 2px 0 0 0;
        }}
        .breadcrumb {{
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 0.08em;
            color: {VIOLET};
            margin: 0 0 2px 0;
        }}
        h1 {{
            font-size: 22px;
            font-weight: 800;
            margin: 0 0 14px 0;
        }}
        .metrics-row {{
            display: flex;
            gap: 10px;
            margin-bottom: 16px;
        }}
        .metric-box {{
            flex: 1;
            background: {VIOLET_SOFT};
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 10px 12px;
        }}
        .metric-label {{
            font-size: 9px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: {VIOLET};
            margin: 0 0 4px 0;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: 800;
            margin: 0;
        }}
        .metric-sub {{
            font-size: 9px;
            color: {MUTED};
            margin: 3px 0 0 0;
        }}
        .section-title {{
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: {VIOLET};
            margin: 16px 0 8px 0;
        }}
        .cavaliers-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}
        .cavalier-label {{
            font-size: 11px;
            font-weight: 700;
            margin: 0 0 2px 0;
        }}
        .cavalier-phrase {{
            font-size: 10px;
            color: {MUTED};
            margin: 0;
        }}
        table.data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 10.5px;
        }}
        table.data-table th {{
            text-align: left;
            font-size: 9px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: {MUTED};
            border-bottom: 1px solid {BORDER};
            padding: 4px 6px;
        }}
        table.data-table td {{
            padding: 4px 6px;
            border-bottom: 1px solid {BORDER};
        }}
        table.data-table th.num, table.data-table td.num {{ text-align: right; }}
        table.data-table tr {{ page-break-inside: avoid; }}
        .footer {{
            margin-top: 18px;
            padding-top: 8px;
            border-top: 1px solid {BORDER};
            font-size: 8.5px;
            color: {FAINT};
        }}
        .footer p {{ margin: 2px 0; }}
    </style>
    </head>
    <body>
        <div class="header">
            <p class="brand">ORACLE<span> DES LOYERS</span></p>
            <div>{meta_html}</div>
        </div>

        {f'<p class="breadcrumb">{breadcrumb}</p>' if breadcrumb else ''}
        <h1>{title}</h1>

        <div class="metrics-row">
            <div class="metric-box">
                <p class="metric-label">Loyer médian</p>
                <p class="metric-value">{_format_price(loyer_median)} €</p>
                {f'<p class="metric-sub">{loyer_sub}</p>' if loyer_sub else ''}
            </div>
            {estimation_box_html}
            <div class="metric-box">
                <p class="metric-label">Prix m² médian</p>
                <p class="metric-value">{_format_m2(prix_m2_median)} €</p>
            </div>
        </div>

        {cavaliers_html}

        {comparables_html}

        <div class="footer">
            <p>Sources : annonces publiques ({SOURCES_LABEL}), points d'intérêt OpenStreetMap.</p>
            <p>Estimation indicative, pas une expertise. · Page 1/1</p>
        </div>
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
