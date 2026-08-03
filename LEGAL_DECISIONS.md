# Décisions légales / éthiques — Oracle des Loyers

Ce document centralise les décisions produit prises face à des questions légales/éthiques
liées au scraping et à la republication de données de tiers (épic **ORA-80** — « Légal /
éthique — affichage des annonces scrapées »). Contexte général : projet portfolio/démonstrateur
technique, sans société éditrice, sans avocat ni accord contractuel avec les sites sources. Les
décisions ci-dessous sont donc prises **par défaut avec la posture la plus prudente**, pas sur
la base d'un avis juridique formel.

---

## ORA-67 / ORA-93 — Conformité du scraping vis-à-vis des CGU/robots.txt des sites sources

*(rappel des conclusions déjà actées, voir [`README.md`](./README.md#🕵️-anti-détection-des-scrapers--limites-légales)
et le commit `5a5a9c1`, 2026-08-03 — ce document ne les modifie pas, il s'appuie dessus)*

- **Revue robots.txt** : 4 des 6 scrapers (Century21, Orpi, PAP, SeLoger) ciblent des chemins
  explicitement `Disallow`. Décision assumée à l'époque : ne pas modifier les scrapers en
  production, compte tenu de l'usage non commercial, des volumes faibles/temporisés, et de
  l'absence de republication de contenu protégé. Risque résiduel assumé explicitement.
- **Photos** : point déjà vérifié en ORA-93 — **aucun des 6 scrapers ne collecte ni ne stocke de
  colonne photo/image** dans les CSV de sortie (`atomic_csv_writer` dans chaque `scraper_*.py`).
  Seuls des champs texte (titre, prix, lieu, détails) et un champ `Lien` vers l'annonce d'origine
  sont exposés. L'application n'a donc, à ce stade, jamais hébergé de photo scrapée.

## ORA-94 — Héberger les photos des annonces, ou juste un lien + thumbnail ?

**Décision : Option (B) — ne jamais héberger nous-mêmes les photos des annonces scrapées.**
L'application affiche uniquement un lien direct (redirection) vers l'annonce sur le site
source. Pas de téléchargement, pas de copie, pas de re-service d'image depuis notre infra.

### Justification

- Une photo d'annonce est un contenu créé par un tiers (agence, particulier, ou le site qui l'a
  retraitée) et protégé par le droit d'auteur. La télécharger puis la republier sur notre propre
  infrastructure constitue un acte de reproduction et de représentation qui nécessiterait en
  principe une autorisation — qu'aucun des 6 sites sources ne nous a donnée.
- Contrairement au texte structuré (prix, surface, localisation — des faits, non protégeables en
  tant que tels), une photographie est une œuvre à part entière : le risque juridique (mise en
  demeure, DMCA/notice-and-takedown, atteinte à l'image de marque du site source) est
  qualitativement plus élevé que celui déjà assumé pour le texte scrapé en ORA-67.
- Ce projet est un portfolio public, sans société éditrice, sans avocat, sans accord passé avec
  Century21/Orpi/SeLoger/PAP/ParuVendu/Vizzit. En l'absence de tout élément dans les CGU
  consultées qui autoriserait explicitement la réutilisation d'images, la posture par défaut la
  plus sûre est de ne pas reproduire ces images du tout.
- Un lien de redirection vers l'annonce d'origine correspond au modèle « agrégateur / moteur de
  recherche » (comme un comparateur qui renvoie vers la source) : c'est l'usage le moins exposé
  juridiquement, et il est cohérent avec l'absence de colonne photo déjà constatée en ORA-93 —
  cette décision ne fait qu'entériner et formaliser un état de fait déjà en place dans les
  scrapers.
- **Vérification des CGU par site** : aucun des documents produits en ORA-67/ORA-93 (revue
  robots.txt du 2026-08-03, cf. `README.md`) ne mentionne d'autorisation explicite de
  réutilisation d'images pour l'un des 6 sites sources. Si une future revue CGU venait à établir
  qu'un site autorise explicitement la réutilisation de ses visuels, la décision pourrait être
  révisée *pour ce site précis uniquement* — mais en l'état, aucun site ne bénéficie de cette
  exception.
- Un thumbnail « généré par nous à partir d'une capture » (screenshot de la page source) a été
  écarté pour la même raison : une capture d'écran reproduit la mise en page et les visuels du
  site source, ce qui pose le même risque de reproduction non autorisée qu'un hébergement direct
  de photo. Aucun thumbnail basé sur du contenu du site source n'est retenu.

### Implication concrète pour les tickets frontend à venir

- **ORA-87 (`AnnonceCard`)** : le composant ne doit **pas** afficher de balise `<img>` pointant
  vers une photo scrapée, ni vers une capture d'écran du site source. Il peut afficher un visuel
  purement générique et non dérivé du site source (icône, pictogramme, illustration maison
  produite en interne, dégradé de couleur selon le type de bien...), ou ne pas afficher de visuel
  du tout — mais jamais une image provenant de l'annonce elle-même.
- **ORA-88** : toute évolution de l'affichage liste/grille des annonces doit respecter la même
  contrainte : aucune image tierce hébergée, quel que soit le format d'affichage retenu.
- **ORA-89 (clic → redirection)** : le clic sur une annonce (carte, titre, ou éventuel visuel
  générique) doit ouvrir un lien externe vers l'annonce d'origine (champ `Lien` déjà présent dans
  les CSV scrapés), typiquement `target="_blank" rel="noopener noreferrer"`, plutôt que de tenter
  de reproduire le contenu de l'annonce (photos incluses) dans l'UI de l'application.
- Si un besoin de « thumbnail » réapparaît malgré cette décision, il devra être traité comme un
  nouveau ticket dérivé de l'épic ORA-80, avec une revue CGU explicite site par site avant toute
  implémentation — pas une décision à prendre au niveau du composant frontend.

---

*Ce document reflète l'état des décisions à la date indiquée dans l'historique Git de ce fichier.
Toute nouvelle question légale/éthique relevant de l'épic ORA-80 (ou d'un autre sujet légal du
projet) doit être ajoutée ici plutôt que dispersée dans les tickets individuels, pour garder une
vue d'ensemble cohérente des postures assumées par le projet.*
