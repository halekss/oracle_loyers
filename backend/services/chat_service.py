import os
import re
import unicodedata


class ChatService:
    DEFAULT_MODEL = "gemini-2.5-flash"
    DEFAULT_MAX_OUTPUT_TOKENS = 800
    DEFAULT_TEMPERATURE = 0.7
    MAX_CONTEXT_LISTINGS = 12

    def __init__(self):
        self.model_name = os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)
        self.max_output_tokens = self._read_int_env(
            "GEMINI_MAX_OUTPUT_TOKENS",
            self.DEFAULT_MAX_OUTPUT_TOKENS,
        )
        self.temperature = self._read_float_env(
            "GEMINI_TEMPERATURE",
            self.DEFAULT_TEMPERATURE,
        )
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()

        self.system_prompt = """
Tu es Immotep, conseiller immobilier lyonnais sarcastique, direct et factuel.
Ta voix est mordante, mais présentable pour une démonstration portfolio: pas d'insulte gratuite, pas de vulgarité, pas d'emoji.

Règles de réponse:
- Réponds en 3 à 5 phrases maximum.
- Utilise les données disponibles au lieu d'inventer.
- Quand un bien ou un secteur est évoqué, cite le prix, le quartier et la surface quand ils sont disponibles.
- Si le contexte est incomplet, dis ce qui manque, mais exploite quand même les annonces et signaux fournis.
- Garde un ton cynique léger: une pique courte suffit, le fond doit rester fiable.
"""

    @staticmethod
    def _read_int_env(name, default):
        try:
            return int(os.getenv(name, default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _read_float_env(name, default):
        try:
            return float(os.getenv(name, default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _extract_quartier(context_str):
        if not context_str or "Quartier:" not in context_str:
            return None

        try:
            return context_str.split("Quartier:", 1)[1].split(",", 1)[0].strip()
        except (IndexError, AttributeError):
            return None

    @staticmethod
    def _normalize_text(value):
        normalized = unicodedata.normalize("NFKD", str(value or ""))
        return "".join(char for char in normalized if not unicodedata.combining(char)).lower()

    def _compact_text(self, value):
        return re.sub(r"[^a-z0-9]+", "", self._normalize_text(value))

    def _searchable_text(self, value):
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", self._normalize_text(value))).strip()

    @staticmethod
    def _has_word_sequence(source, target, min_words=2):
        words = [word for word in source.split() if len(word) > 1]
        if len(words) < min_words:
            return False
        for size in range(len(words), min_words - 1, -1):
            for start in range(0, len(words) - size + 1):
                if " ".join(words[start:start + size]) in target:
                    return True
        return False

    def _extract_postal_code(self, *texts):
        codes = self._extract_postal_codes(*texts)
        return codes[0] if codes else None

    def _extract_postal_codes(self, *texts):
        combined = " ".join(str(text or "") for text in texts)
        normalized = self._normalize_text(combined)
        codes = []

        for postal_match in re.finditer(r"\b6900([1-9])\b", normalized):
            code = 69000 + int(postal_match.group(1))
            if code not in codes:
                codes.append(code)

        for arrondissement_match in re.finditer(r"\blyon\s*([1-9])(?:er|eme|e|è|ème)?\b", normalized):
            code = 69000 + int(arrondissement_match.group(1))
            if code not in codes:
                codes.append(code)

        lyon_group_match = re.search(r"\blyon\s+((?:[1-9](?:er|eme|e|è|ème)?(?:\s*(?:,|et|ou|/)\s*)?)+)", normalized)
        if lyon_group_match:
            for number_match in re.finditer(r"\b([1-9])(?:er|eme|e|è|ème)?\b", lyon_group_match.group(1)):
                code = 69000 + int(number_match.group(1))
                if code not in codes:
                    codes.append(code)

        return codes

    @staticmethod
    def _type_matches(series, type_local):
        if not type_local:
            return series.notna()

        if isinstance(type_local, list):
            mask = series.notna() & False
            for item in type_local:
                mask = mask | ChatService._type_matches(series, item)
            return mask

        normalized = series.fillna("").astype(str).str.lower()
        if type_local == "T1":
            return normalized.str.contains("t1|studio", regex=True)
        if type_local == "T4+":
            return normalized.str.contains("t4|t5|maison|grand", regex=True)
        return normalized.str.contains(type_local.lower(), regex=False)

    def parse_query(self, user_message, context_str="", df=None):
        query = self._normalize_text(user_message)
        context = self._normalize_text(context_str)
        combined = f"{context} {query}"

        intent = "search"
        if any(word in query for word in ["compare", "comparaison", "versus", " vs "]):
            intent = "compare"
        elif any(word in query for word in ["focus", "zoom", "centre", "montre", "carte"]):
            intent = "focus"

        type_locals = []
        type_patterns = [
            ("T1", r"\b(studio|t1|1 piece)\b"),
            ("T2", r"\b(t2|2 pieces?)\b"),
            ("T3", r"\b(t3|3 pieces?)\b"),
            ("T4+", r"\b(t4|t5|4 pieces?|5 pieces?|maison)\b"),
        ]
        for label, pattern in type_patterns:
            if re.search(pattern, combined) and label not in type_locals:
                type_locals.append(label)
        type_local = type_locals[0] if type_locals else None

        budget_max = None
        budget_patterns = [
            r"(?:moins de|budget|max(?:imum)?|jusqu.?a)\s*(\d{3,5})",
            r"(\d{3,5})\s*(?:eur|€)\s*(?:max|maximum)?",
        ]
        for pattern in budget_patterns:
            match = re.search(pattern, combined)
            if match:
                budget_max = int(match.group(1))
                break

        surface_min = None
        surface_match = re.search(r"(?:au moins|min(?:imum)?)\s*(\d{2,3})\s*m", combined)
        if surface_match:
            surface_min = int(surface_match.group(1))

        preferences = []
        wants_bar_near = bool(
            re.search(r"\bbar[s]?\b.{0,25}\b(pas loin|proche|a cote|à cote|autour|pres|près)\b", combined)
            or re.search(r"\b(pas loin|proche|a cote|à cote|autour|pres|près)\b.{0,25}\bbar[s]?\b", combined)
        )
        preference_terms = {
            "quiet": ["calme", "bruit", "silencieux", "tranquille"],
            "shops": ["commerce", "commerces", "supermarch", "supermarche", "superu", "super u", "courses"],
            "transport": ["metro", "tram", "transport", "gare"],
            "avoid_nightlife": ["bar", "bars", "discotheque", "nuit"],
        }
        for key, terms in preference_terms.items():
            if key == "avoid_nightlife" and wants_bar_near:
                continue
            if any(term in combined for term in terms):
                preferences.append(key)
        if wants_bar_near:
            preferences.append("bar_near")

        locations = self._extract_locations(user_message, context_str, df)
        postal_codes = self._extract_postal_codes(context_str, user_message)
        postal_code = postal_codes[0] if postal_codes else None

        return {
            "intent": intent,
            "locations": locations,
            "postal_code": postal_code,
            "postal_codes": postal_codes,
            "type_local": type_local,
            "type_locals": type_locals,
            "budget_max": budget_max,
            "surface_min": surface_min,
            "preferences": preferences,
        }

    @staticmethod
    def _has_shop_evidence(row):
        description = ChatService._normalize_text(row.get("description", ""))
        return any(term in description for term in ["commerce", "commerces", "superu", "super u", "supermarch"])

    def _extract_locations(self, user_message, context_str="", df=None):
        combined = self._normalize_text(f"{context_str} {user_message}")
        searchable_combined = self._searchable_text(f"{context_str} {user_message}")
        matches = []

        if df is not None and "quartier" in df.columns:
            quartiers = [
                str(value).strip()
                for value in df["quartier"].dropna().unique().tolist()
                if str(value).strip()
            ]
            for quartier in sorted(quartiers, key=len, reverse=True):
                normalized = self._normalize_text(quartier)
                searchable = self._searchable_text(quartier)
                compact = self._compact_text(quartier)
                compact_combined = self._compact_text(combined)
                if (
                    len(normalized) >= 3
                    and (
                        normalized in combined
                        or searchable in searchable_combined
                        or self._has_word_sequence(searchable, searchable_combined)
                        or compact in compact_combined
                    )
                    and quartier not in matches
                ):
                    matches.append(quartier)

        postal_codes = self._extract_postal_codes(context_str, user_message)
        if postal_codes:
            for postal_code in postal_codes:
                label = f"Lyon {postal_code - 69000}"
                if label not in matches:
                    matches.append(label)

        return matches[:4]

    def _apply_parsed_filters(self, df, parsed):
        if df is None or getattr(df, "empty", True):
            return df

        filtered = df
        if parsed.get("postal_code") and "code_postal" in filtered.columns:
            postal_values = filtered["code_postal"].astype(str).str.extract(r"(\d+)")[0]
            postal_filtered = filtered[postal_values == str(parsed["postal_code"])]
            if not postal_filtered.empty:
                filtered = postal_filtered

        if parsed.get("locations") and "quartier" in filtered.columns:
            location_masks = []
            normalized_quartiers = filtered["quartier"].astype(str).map(self._normalize_text)
            for location in parsed["locations"]:
                normalized_location = self._normalize_text(location)
                if normalized_location.startswith("lyon "):
                    continue
                location_masks.append(normalized_quartiers.str.contains(re.escape(normalized_location), na=False))
            if location_masks:
                mask = location_masks[0]
                for extra_mask in location_masks[1:]:
                    mask = mask | extra_mask
                location_filtered = filtered[mask]
                if not location_filtered.empty:
                    filtered = location_filtered

        type_filter = parsed.get("type_locals") or parsed.get("type_local")
        if type_filter and "type_local" in filtered.columns:
            type_filtered = filtered[self._type_matches(filtered["type_local"], type_filter)]
            if not type_filtered.empty:
                filtered = type_filtered

        if parsed.get("budget_max") and "prix" in filtered.columns:
            price_filtered = filtered[filtered["prix"] <= parsed["budget_max"]]
            if not price_filtered.empty:
                filtered = price_filtered

        if parsed.get("surface_min") and "surface" in filtered.columns:
            surface_filtered = filtered[filtered["surface"] >= parsed["surface_min"]]
            if not surface_filtered.empty:
                filtered = surface_filtered

        return filtered

    def _summarize_group(self, df, label):
        clean = df.dropna(subset=["prix", "surface"])
        if clean.empty:
            return None

        center = None
        if {"latitude", "longitude"}.issubset(clean.columns):
            coords = clean.dropna(subset=["latitude", "longitude"])
            if not coords.empty:
                center = {
                    "lat": round(float(coords["latitude"].mean()), 6),
                    "lng": round(float(coords["longitude"].mean()), 6),
                }

        return {
            "quartier": label,
            "count": int(len(clean)),
            "prix_moyen": round(float(clean["prix"].mean()), 0),
            "surface_moyenne": round(float(clean["surface"].mean()), 1),
            "prix_m2_moyen": round(float((clean["prix"] / clean["surface"]).mean()), 1),
            "center": center,
        }

    def _build_comparisons(self, df, parsed):
        if df is None or getattr(df, "empty", True) or not parsed.get("locations"):
            return []

        comparisons = []
        for location in parsed["locations"]:
            location_df = df
            normalized_location = self._normalize_text(location)

            if normalized_location.startswith("lyon "):
                arrondissement_match = re.search(r"\blyon\s*([1-9])\b", normalized_location)
                postal_code = 69000 + int(arrondissement_match.group(1)) if arrondissement_match else parsed.get("postal_code")
                postal_values = location_df["code_postal"].astype(str).str.extract(r"(\d+)")[0]
                location_df = location_df[postal_values == str(postal_code)]
            elif "quartier" in location_df.columns:
                normalized_quartiers = location_df["quartier"].astype(str).map(self._normalize_text)
                location_df = location_df[normalized_quartiers.str.contains(re.escape(normalized_location), na=False)]

            type_filter = parsed.get("type_locals") or parsed.get("type_local")
            if type_filter and "type_local" in location_df.columns:
                location_df = location_df[self._type_matches(location_df["type_local"], type_filter)]

            summary = self._summarize_group(location_df, location)
            if summary:
                comparisons.append(summary)

        return sorted(comparisons, key=lambda item: item["prix_moyen"])

    def _build_recommendations(self, df, parsed):
        filtered = self._apply_parsed_filters(df, parsed)
        if filtered is None or getattr(filtered, "empty", True):
            return []

        selected = self._select_relevant_listings(
            filtered,
            postal_code=parsed.get("postal_code"),
            user_message=" ".join(parsed.get("preferences", [])),
        ).head(5)

        recommendations = []
        for _, row in selected.iterrows():
            try:
                item = {
                    "quartier": str(row.get("quartier", "Inconnu")),
                    "type_local": str(row.get("type_local", "?")),
                    "prix": round(float(row.get("prix", 0)), 0),
                    "surface": round(float(row.get("surface", 0)), 1),
                    "why": self._recommendation_reason(row, parsed),
                }
                if row.get("latitude") and row.get("longitude"):
                    item["lat"] = round(float(row.get("latitude")), 6)
                    item["lng"] = round(float(row.get("longitude")), 6)
                recommendations.append(item)
            except (TypeError, ValueError):
                continue

        return recommendations

    def _recommendation_reason(self, row, parsed):
        reasons = []
        if "quiet" in parsed.get("preferences", []):
            try:
                bars = float(row.get("nb_vice_bar_500m", 0) or 0)
                clubs = float(row.get("nb_nuisance_discothèque_500m", 0) or 0)
                if bars <= 2 and clubs == 0:
                    reasons.append("profil plutôt calme selon les signaux bruit")
            except (TypeError, ValueError):
                pass
        if "shops" in parsed.get("preferences", []):
            if self._has_shop_evidence(row):
                reasons.append("commerces mentionnés dans l'annonce")
        if "bar_near" in parsed.get("preferences", []):
            try:
                bars = float(row.get("nb_vice_bar_500m", 0) or 0)
                distance = float(row.get("dist_vice_bar", 0) or 0)
                if bars > 0:
                    reasons.append(f"{bars:.0f} bar(s) à 500m, le plus proche à {distance:.0f}m")
            except (TypeError, ValueError):
                pass
        return ", ".join(reasons) if reasons else "meilleur compromis dans les annonces filtrées"

    def _select_relevant_listings(self, df, quartier_filter=None, postal_code=None, user_message=""):
        if df is None or getattr(df, "empty", True):
            return df

        listings = df
        if quartier_filter and "quartier" in df.columns:
            mask = df["quartier"].astype(str).str.contains(quartier_filter, case=False, na=False)
            filtered = df[mask]
            if not filtered.empty:
                listings = filtered

        if postal_code and "code_postal" in df.columns:
            postal_values = df["code_postal"].astype(str).str.extract(r"(\d+)")[0]
            filtered = df[postal_values == str(postal_code)]
            if not filtered.empty:
                listings = filtered

        query = self._normalize_text(user_message)
        quality_keywords = [
            "calme",
            "supermarche",
            "supermarches",
            "superu",
            "commerce",
            "commerces",
            "bruit",
            "silencieux",
            "tranquille",
        ]

        def score(row):
            value = 0
            description = self._normalize_text(row.get("description", ""))
            quartier = self._normalize_text(row.get("quartier", ""))

            for keyword in quality_keywords:
                if keyword in query and keyword in description:
                    value += 5

            if "supermarche" in query and ("superu" in description or "super u" in description):
                value += 6
            if "bruit" in query or "calme" in query:
                value += self._quiet_score(row)
            if "bar_near" in query:
                value += self._bar_near_score(row)
            if quartier and quartier in query:
                value += 2

            return value

        if not listings.empty:
            listings = listings.assign(_rag_score=listings.apply(score, axis=1))
            listings = listings.sort_values(
                by=["_rag_score", "prix"],
                ascending=[False, True],
                kind="mergesort",
            )

        return listings.head(self.MAX_CONTEXT_LISTINGS)

    @staticmethod
    def _quiet_score(row):
        score = 0
        for column in [
            "nb_vice_bar_500m",
            "nb_nuisance_discothèque_500m",
            "nb_nuisance_salle_de_concert_500m",
            "nb_nuisance_station_service_500m",
        ]:
            try:
                count = float(row.get(column, 0) or 0)
                if count == 0:
                    score += 2
                elif count <= 2:
                    score += 1
                elif count >= 8:
                    score -= 2
            except (TypeError, ValueError):
                continue
        return score

    @staticmethod
    def _bar_near_score(row):
        try:
            bars = float(row.get("nb_vice_bar_500m", 0) or 0)
            distance = float(row.get("dist_vice_bar", 9999) or 9999)
        except (TypeError, ValueError):
            return 0

        score = min(int(bars), 5)
        if distance <= 150:
            score += 5
        elif distance <= 300:
            score += 3
        elif distance <= 500:
            score += 1
        return score

    def _format_listings(self, df, quartier_filter=None, postal_code=None, user_message=""):
        if df is None or getattr(df, "empty", True):
            return "Aucune annonce exploitable dans l'extrait."

        listings = self._select_relevant_listings(df, quartier_filter, postal_code, user_message)
        lines = []

        for index, row in listings.iterrows():
            try:
                quartier = str(row.get("quartier", "Inconnu")).strip() or "Inconnu"
                prix = float(row.get("prix", 0))
                surface = float(row.get("surface", 0))
                type_local = str(row.get("type_local", "?")).strip() or "?"

                if prix <= 0 or surface <= 0:
                    continue

                details = [
                    f"{type_local}",
                    f"{quartier}",
                    f"{prix:.0f} EUR",
                    f"{surface:.0f} m2",
                ]

                prix_m2 = row.get("prix_m2")
                try:
                    if prix_m2 and float(prix_m2) > 0:
                        details.append(f"{float(prix_m2):.0f} EUR/m2")
                except (TypeError, ValueError):
                    pass

                signal_text = self._format_quality_signals(row)
                if signal_text:
                    details.append(signal_text)

                description = str(row.get("description", "") or "").strip()
                if description:
                    details.append(f"description: {description[:220]}")

                lines.append("- " + " | ".join(details))
            except (TypeError, ValueError):
                continue

        return "\n".join(lines) if lines else "Aucune annonce exploitable dans l'extrait."

    @staticmethod
    def _format_quality_signals(row):
        labels = [
            ("nb_vice_bar_500m", "bars 500m"),
            ("dist_vice_bar", "bar le plus proche"),
            ("nb_nuisance_discothèque_500m", "discothèques 500m"),
            ("dist_nuisance_discothèque", "discothèque la plus proche"),
            ("nb_nuisance_salle_de_concert_500m", "salles de concert 500m"),
            ("nb_nuisance_station_service_500m", "stations-service 500m"),
        ]
        parts = []

        for column, label in labels:
            value = row.get(column)
            try:
                if value is None or value == "":
                    continue
                number = float(value)
            except (TypeError, ValueError):
                continue

            if column.startswith("dist_"):
                parts.append(f"{label}: {number:.0f}m")
            else:
                parts.append(f"{label}: {number:.0f}")

        return "signaux: " + ", ".join(parts) if parts else ""

    def _build_prompt(self, user_message, context_str, data_text, parsed=None, comparisons=None):
        clean_context = context_str.strip() if context_str else "Aucun contexte de scan fourni."
        parsed_text = parsed or {}
        comparison_text = ""
        if comparisons:
            comparison_lines = [
                (
                    f"- {item['quartier']}: {item['prix_moyen']:.0f} EUR moyen, "
                    f"{item['prix_m2_moyen']:.1f} EUR/m2, {item['count']} annonces"
                )
                for item in comparisons
            ]
            comparison_text = "\nComparaison calculée localement:\n" + "\n".join(comparison_lines)

        return f"""
Contexte du scan:
{clean_context}

Demande parsée:
{parsed_text}
{comparison_text}

Annonces pertinentes disponibles:
{data_text}

Question:
{user_message}

Réponds comme Immotep en respectant les règles système.
Pour une demande sur le calme, le bruit ou les commerces, exploite les descriptions et les signaux fournis. Ne dis pas qu'il n'y a aucune annonce si l'extrait en contient.
Pour une comparaison, cite les moyennes calculées et le nombre d'annonces avant ton verdict.
""".strip()

    def _generate_with_gemini(self, prompt):
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                max_output_tokens=self.max_output_tokens,
                temperature=self.temperature,
            ),
        )
        return (response.text or "").strip()

    @staticmethod
    def _map_focus_from(comparisons, recommendations):
        for item in comparisons or []:
            center = item.get("center")
            if center:
                return {
                    "quartier": item.get("quartier"),
                    "lat": center["lat"],
                    "lng": center["lng"],
                    "zoom": 15,
                }

        for item in recommendations or []:
            if item.get("lat") and item.get("lng"):
                return {
                    "quartier": item.get("quartier"),
                    "lat": item["lat"],
                    "lng": item["lng"],
                    "zoom": 16,
                }

        return None

    @staticmethod
    def _format_money(value):
        return f"{round(float(value)):.0f} EUR"

    def _build_grounded_response(self, parsed, comparisons, recommendations):
        parsed_types = parsed.get("type_locals") or ([parsed["type_local"]] if parsed.get("type_local") else [])
        type_label = "/".join(parsed_types)

        if parsed.get("intent") == "compare" and comparisons:
            if len(comparisons) == 1:
                item = comparisons[0]
                type_text = f" pour un {type_label}" if type_label else ""
                return (
                    f"Je n'ai qu'un secteur exploitable: {item['quartier']}{type_text}, "
                    f"{self._format_money(item['prix_moyen'])} de loyer moyen, "
                    f"{item['prix_m2_moyen']:.1f} EUR/m2, sur {item['count']} annonces. "
                    "Pour comparer, il me faut un deuxième secteur présent dans la base; sinon c'est un duel contre un mur, brillant mais peu instructif."
                )

            cheapest = comparisons[0]
            most_expensive = comparisons[-1]
            type_text = f" pour un {type_label}" if type_label else ""
            lines = [
                f"Comparaison{type_text}: "
                + "; ".join(
                    f"{item['quartier']} tourne à {self._format_money(item['prix_moyen'])} "
                    f"({item['prix_m2_moyen']:.1f} EUR/m2, {item['count']} annonces)"
                    for item in comparisons
                )
                + ".",
                (
                    f"Le moins cher dans l'extrait est {cheapest['quartier']}; "
                    f"le plus cher est {most_expensive['quartier']}."
                ),
            ]
            if most_expensive["prix_moyen"] != cheapest["prix_moyen"]:
                delta = most_expensive["prix_moyen"] - cheapest["prix_moyen"]
                lines.append(
                    f"Ecart moyen: {self._format_money(delta)} par mois, "
                    "donc oui, le choix du quartier n'est pas juste une coquetterie de carte postale."
                )
            return " ".join(lines)

        if recommendations:
            first = recommendations[0]
            type_text = type_label or first.get("type_local") or "bien"
            locations = parsed.get("locations") or []
            intro_location = locations[0] if locations else first.get("quartier", "ce secteur")
            wants_shops = "shops" in parsed.get("preferences", [])
            has_shop_data = any(self._has_shop_evidence(item) for item in recommendations)
            response = (
                f"Pour {intro_location}, j'ai des pistes en {type_text}. "
                f"La meilleure à sortir du lot: {first.get('type_local', type_text)} à {first['quartier']}, "
                f"{self._format_money(first['prix'])} pour {first['surface']} m2."
            )
            if first.get("why"):
                response += f" Pourquoi: {first['why']}."
            if len(recommendations) > 1:
                second = recommendations[1]
                response += (
                    f" En alternative, {second.get('type_local', type_text)} à {second['quartier']}, "
                    f"{self._format_money(second['prix'])} pour {second['surface']} m2."
                )
            if wants_shops and not has_shop_data:
                response += (
                    " Pour les supermarchés, ma base actuelle n'a pas de signal fiable dans ces annonces; "
                    "je peux te parler du bruit et des prix, pas inventer un Carrefour pour décorer."
                )
            return response + " Voilà, c'est moins romantique qu'une vitrine d'agence, mais au moins c'est chiffré."

        return None

    def get_chat_result(self, user_message, context_str, dataframe):
        parsed = self.parse_query(user_message, context_str, dataframe)
        quartier_cible = self._extract_quartier(context_str)
        postal_code = parsed.get("postal_code")
        comparisons = self._build_comparisons(dataframe, parsed)
        recommendations = self._build_recommendations(dataframe, parsed)
        map_focus = self._map_focus_from(comparisons, recommendations)
        data_text = self._format_listings(dataframe, quartier_cible, postal_code, user_message)
        prompt = self._build_prompt(user_message, context_str, data_text, parsed, comparisons)
        grounded_response = self._build_grounded_response(parsed, comparisons, recommendations)

        if grounded_response:
            return {
                "response": grounded_response,
                "intent": parsed["intent"],
                "parsed": parsed,
                "recommendations": recommendations,
                "comparisons": comparisons,
                "map_focus": map_focus,
            }

        if not self.api_key:
            return {
                "response": (
                    "La configuration IA est absente côté serveur. "
                    "Ajoutez GEMINI_API_KEY pour activer Immotep."
                ),
                "intent": "error",
                "parsed": parsed,
                "recommendations": recommendations,
                "comparisons": comparisons,
                "map_focus": map_focus,
            }

        try:
            response_text = self._generate_with_gemini(prompt)
            if response_text:
                return {
                    "response": response_text,
                    "intent": parsed["intent"],
                    "parsed": parsed,
                    "recommendations": recommendations,
                    "comparisons": comparisons,
                    "map_focus": map_focus,
                }
            return {
                "response": "Gemini n'a renvoyé aucun texte exploitable. Même le marché lyonnais est plus bavard.",
                "intent": parsed["intent"],
                "parsed": parsed,
                "recommendations": recommendations,
                "comparisons": comparisons,
                "map_focus": map_focus,
            }
        except TimeoutError:
            return {
                "response": (
                    "Le service IA met trop de temps à répondre. "
                    "Réessaie dans un instant, Immotep range ses dossiers."
                ),
                "intent": parsed["intent"],
                "parsed": parsed,
                "recommendations": recommendations,
                "comparisons": comparisons,
                "map_focus": map_focus,
            }
        except Exception as exc:
            message = str(exc).lower()
            if "quota" in message or "429" in message or "resource_exhausted" in message:
                return {
                    "response": (
                        "Le quota IA est temporairement atteint. "
                        "Réessaie plus tard, le marché peut attendre deux minutes."
                    ),
                    "intent": parsed["intent"],
                    "parsed": parsed,
                    "recommendations": recommendations,
                    "comparisons": comparisons,
                    "map_focus": map_focus,
                }

            print(f"Erreur provider Gemini: {type(exc).__name__} - {exc}")
            return {
                "response": (
                    "Le service IA est indisponible pour le moment. "
                    "Réessaie dans quelques instants."
                ),
                "intent": parsed["intent"],
                "parsed": parsed,
                "recommendations": recommendations,
                "comparisons": comparisons,
                "map_focus": map_focus,
            }

    def get_response(self, user_message, context_str, dataframe):
        return self.get_chat_result(user_message, context_str, dataframe)["response"]
