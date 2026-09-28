import { test, expect } from '@playwright/test';

// Non-régression ORA-196 : cliquer un ping vert (annonce) sur la carte doit
// à la fois rouvrir le popup Leaflet d'origine (type/prix/quartier/"Voir
// l'annonce ↗") ET ouvrir la Fiche complète du rail (avec photo), sans que
// les cavaliers (POI) n'interceptent le clic ni n'ouvrent eux-mêmes la
// Fiche — cf. MAP_CONTRACT.md (LISTING_SELECTED/HIGHLIGHT_LISTING) et
// generate_map.py (CAVALIERS_PANE, z-index 390, sous l'overlayPane 400 des
// CircleMarker d'annonces).
//
// Les clics sont de VRAIS clics souris à la position pixel du marker
// (latLngToContainerPoint + page.mouse.click), pas un `marker.fire('click')`
// programmatique : seul un clic à la bonne coordonnée écran peut détecter
// une régression d'interception par une pane mal ordonnée — c'est
// exactement la méthode qui a permis de diagnostiquer la régression
// d'origine (échantillonnage `document.elementFromPoint`).

const CARTE_IFRAME_TITLE = 'Carte Oracle';
const BACKEND_URL = 'http://localhost:5055';

// Le quartier le plus dense en annonces est le meilleur pari pour qu'au
// moins l'une d'elles tombe dans un rayon de 500 m autour de son centroïde
// géocodé (le jeu de données réel évolue — un quartier fixe comme "Gerland"
// n'est pas garanti d'avoir une annonce assez proche à un instant donné).
async function pickDensestQuartier(request) {
  const res = await request.get(`${BACKEND_URL}/api/annonces?ville=lyon&per_page=500&sort=prix_m2&order=asc`);
  const data = await res.json();
  const counts = {};
  for (const item of data.items || []) {
    if (item.quartier) counts[item.quartier] = (counts[item.quartier] || 0) + 1;
  }
  const [best] = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (!best) throw new Error('Aucune annonce avec quartier renseigné (GET /api/annonces)');
  return best[0];
}

async function getMapFrame(page) {
  await expect(page.getByTitle(CARTE_IFRAME_TITLE)).toBeVisible();
  const frame = page.frames().find((f) => f.url().includes('map_pings_'));
  if (!frame) throw new Error('Iframe carte introuvable');
  await frame.waitForFunction(
    () => Boolean(window.oracleImmoMarkersById) && Object.keys(window.oracleImmoMarkersById).length > 0,
    null,
    { timeout: 15_000 },
  );
  return frame;
}

async function clickAtLatLng(page, frame, { lat, lng }) {
  const iframeEl = page.locator(`iframe[title="${CARTE_IFRAME_TITLE}"]`);
  const box = await iframeEl.boundingBox();
  const point = await frame.evaluate(({ lat: la, lng: lo }) => {
    const mapVarName = Object.keys(window).find((k) => k.startsWith('map_'));
    const map = window[mapVarName];
    const pt = map.latLngToContainerPoint(window.L.latLng(la, lo));
    return { x: pt.x, y: pt.y };
  }, { lat, lng });
  await page.mouse.click(box.x + point.x, box.y + point.y);
}

// Popup Leaflet natif (bind_popup, build_immo_popup_html) : contenu ORIGINAL
// (type, prix, quartier, lien) restauré par ORA-196, indépendant de la Fiche.
async function expectAnnoncePopupOpen(frame) {
  const popup = frame.locator('.leaflet-popup-content');
  await expect(popup).toBeVisible();
  await expect(popup.getByText("Voir l'annonce ↗")).toBeVisible();
}

// Fiche du rail (#panel-sheet, vue "Fiche") : image réelle chargée OU repli
// (icône générique) — jamais une image cassée à l'écran (AnnonceIllustration,
// onError). `img[alt]` : la fiche passe un alt descriptif (jamais l'alt vide
// décoratif utilisé par les cartes de la liste).
async function expectFicheOpen(page) {
  const panelSheet = page.locator('#panel-sheet');
  await expect(panelSheet.getByText('Fiche annonce')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Fiche' })).not.toHaveAttribute('aria-disabled', 'true');

  const img = panelSheet.locator('img[alt]').first();
  const fallbackIcon = panelSheet.locator('svg[aria-hidden="true"]').first();
  await expect(img.or(fallbackIcon)).toBeVisible();
  if (await img.count()) {
    // Si l'<img> reste montée, elle a fini de charger sans erreur (sinon
    // onError l'aurait remplacée par le repli SVG) : jamais d'icône cassée.
    await expect.poll(() => img.evaluate((el) => el.complete && el.naturalWidth > 0)).toBe(true);
  }
}

// Clique le marker à `latlng`, attend la requête réelle GET
// /api/annonces/<id> déclenchée par l'ouverture de la Fiche (preuve que
// LISTING_SELECTED a bien été reçu et traité), et renvoie son id.
async function clickMarkerAndAwaitFiche(page, frame, latlng) {
  const [detailResponse] = await Promise.all([
    page.waitForResponse((res) => /\/api\/annonces\/\d+$/.test(res.url()) && res.ok()),
    clickAtLatLng(page, frame, latlng),
  ]);
  const id = Number(new URL(detailResponse.url()).pathname.match(/(\d+)$/)[1]);
  await expectAnnoncePopupOpen(frame);
  await expectFicheOpen(page);
  return id;
}

test.describe('Clic sur un ping d\'annonce — popup + Fiche (ORA-196)', () => {
  test('sans scan : cliquer un ping vert ouvre le popup ET la Fiche, avec une image valide', async ({ page }) => {
    await page.goto('/');
    const frame = await getMapFrame(page);

    const firstMarker = await frame.evaluate(() => {
      const marker = Object.values(window.oracleImmoMarkersById)[0];
      const { lat, lng } = marker.getLatLng();
      return { lat, lng };
    });

    await clickMarkerAndAwaitFiche(page, frame, firstMarker);
  });

  test('avec un scan et un rayon de 500 m actif, un ping à l\'intérieur du cercle ouvre aussi le popup et la Fiche', async ({ page, request }) => {
    const quartier = await pickDensestQuartier(request);

    await page.goto('/');
    const frame = await getMapFrame(page);

    await page.getByRole('button', { name: 'Recherche', exact: true }).click();
    const panelSheet = page.locator('#panel-sheet');
    await panelSheet.getByLabel('Quartier à scanner').fill(quartier);
    await Promise.all([
      page.waitForResponse((res) => res.url().includes('/api/quartier-stats') && res.ok()),
      panelSheet.getByRole('button', { name: 'Scan', exact: true }).click(),
    ]);

    await page.getByRole('button', { name: 'Calques', exact: true }).click();
    // Recliquer sur le préréglage déjà actif le désélectionne (CalquesView.jsx,
    // RadiusSelector) — 500 m est le rayon par défaut après un scan : ne
    // cliquer que s'il n'est pas déjà sélectionné, pour ne pas l'éteindre.
    const radius500 = page.getByRole('button', { name: '500 m', exact: true });
    if ((await radius500.getAttribute('aria-pressed')) !== 'true') {
      await radius500.click();
    }
    await frame.waitForFunction(() => Boolean(window.__oracleFocusCircle));

    // Le cercle peut être recréé juste après (SET_FOCUS relancé par un
    // second rendu) : on retente plutôt que de lire `__oracleFocusCircle`
    // une seule fois pendant cette fenêtre de recréation.
    const findTargetInRadius = () => frame.evaluate(() => {
      const circle = window.__oracleFocusCircle;
      if (!circle) return null;
      const center = circle.getLatLng();
      for (const marker of Object.values(window.oracleImmoMarkersById || {})) {
        const latlng = marker.getLatLng();
        if (center.distanceTo(latlng) <= 500) return { lat: latlng.lat, lng: latlng.lng };
      }
      return null;
    });
    let target = null;
    for (let attempt = 0; attempt < 10 && target === null; attempt += 1) {
      target = await findTargetInRadius();
      if (target === null) await page.waitForTimeout(200);
    }
    expect(target, `aucune annonce dans le rayon de 500 m autour de ${quartier} — jeu de données inattendu`).not.toBeNull();

    // `target` est déjà vérifié à <= 500 m du centre du cercle ci-dessus.
    // Cliquer navigue vers la vue "Fiche" (activeView !== 'calques'), ce qui
    // efface `__oracleFocusCircle` (CLEAR_FOCUS, MapComponent.jsx) : la
    // distance ne peut donc plus être revérifiée après coup, elle l'a été
    // avant le clic.
    await clickMarkerAndAwaitFiche(page, frame, target);
  });

  test('cliquer un cavalier (POI) n\'ouvre pas la Fiche — seul son propre popup (nom du lieu) s\'affiche', async ({ page }) => {
    await page.goto('/');
    const frame = await getMapFrame(page);
    await frame.waitForFunction(() => Array.isArray(window.oracleCavalierMarkers) && window.oracleCavalierMarkers.length > 0);

    const cavalier = await frame.evaluate(() => {
      const entry = window.oracleCavalierMarkers[0];
      return { lat: entry.lat, lng: entry.lng };
    });

    await clickAtLatLng(page, frame, cavalier);

    await expect(frame.locator('.leaflet-popup-content')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Fiche' })).toHaveAttribute('aria-disabled', 'true');
    await expect(page.getByText('Fiche annonce')).not.toBeVisible();
  });
});
