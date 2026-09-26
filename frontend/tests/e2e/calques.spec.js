import { test, expect } from '@playwright/test';

// Non-régression de la vue "Calques" (rail desktop) après le correctif du
// script carte qui plantait au chargement (bugs #1/#2/#3/#5/#8, cf.
// MAP_CONTRACT.md) : le fond de carte doit charger de vraies tuiles, chaque
// interrupteur doit réellement piloter le calque correspondant sur la carte
// (dans les deux sens), les 4 familles de cavaliers doivent avoir des
// markers à Lyon, et la page ne doit jamais déborder verticalement.
//
// `window.oracleLayerGroups` (généré par build_layer_groups_script,
// backend/scripts/generate_map.py) expose en lecture, depuis l'iframe, le
// FeatureGroup/GeoJson Folium associé à chaque clé de calque — c'est le
// point d'observation utilisé ici pour vérifier qu'un TOGGLE_LAYER a
// réellement ajouté/retiré le calque sur la carte (pas seulement changé
// l'état React).

const CARTE_IFRAME_TITLE = 'Carte Oracle';

async function getMapFrame(page) {
  await expect(page.getByTitle(CARTE_IFRAME_TITLE)).toBeVisible();
  const frame = page.frames().find((f) => f.url().includes('map_pings_'));
  if (!frame) throw new Error('Iframe carte introuvable');
  await frame.waitForFunction(() => Boolean(window.oracleLayerGroups), null, { timeout: 15_000 });
  return frame;
}

async function isLayerOnMap(frame, key) {
  return frame.evaluate((layerKey) => {
    const mapVarName = Object.keys(window).find((k) => k.startsWith('map_'));
    const map = window[mapVarName];
    const group = window.oracleLayerGroups[layerKey];
    return Boolean(group) && map.hasLayer(group);
  }, key);
}

async function goToCalques(page) {
  await page.getByRole('button', { name: 'Calques', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Calques & 4 cavaliers' })).toBeVisible();
}

// Scanne un quartier via la vue "Recherche" du rail — même parcours que
// l'utilisateur (SearchForm.jsx : champ "Quartier à scanner", bouton submit
// "Scan"). Le rail lui-même porte aussi un item nommé "Scan" (vue une fois
// le scan lancé) : les deux boutons partagent le même nom accessible, d'où
// le scope sur #panel-sheet pour cibler uniquement le bouton du formulaire.
async function scanQuartier(page, quartier) {
  await page.getByRole('button', { name: 'Recherche', exact: true }).click();
  const panelSheet = page.locator('#panel-sheet');
  await panelSheet.getByLabel('Quartier à scanner').fill(quartier);
  await Promise.all([
    page.waitForResponse((res) => res.url().includes('/api/quartier-stats') && res.ok()),
    panelSheet.getByRole('button', { name: 'Scan', exact: true }).click(),
  ]);
}

test.describe('Vue Calques — non-régression', () => {
  test('le fond de carte charge de vraies tuiles (pas le placeholder transparent)', async ({ page }) => {
    await page.goto('/');
    const frame = await getMapFrame(page);

    await frame.waitForFunction(() => {
      const mapVarName = Object.keys(window).find((k) => k.startsWith('map_'));
      const map = window[mapVarName];
      let url = null;
      map.eachLayer((layer) => {
        if (layer instanceof window.L.TileLayer) url = layer._url;
      });
      return url && !url.startsWith('data:image/gif');
    }, null, { timeout: 15_000 });

    const tileCount = await frame.locator('.leaflet-tile-pane img.leaflet-tile').count();
    expect(tileCount).toBeGreaterThan(0);
  });

  test('chaque interrupteur pilote réellement son calque sur la carte, dans les deux sens', async ({ page }) => {
    await page.goto('/');
    const frame = await getMapFrame(page);
    await goToCalques(page);

    const cases = [
      { label: 'Métro & stations', key: 'Metro' },
      { label: 'Funiculaires', key: 'Funicular' },
      { label: '€/m² par arrondissement', key: 'Quartiers' },
      { label: 'Apparts T2', key: 'T2' },
      { label: 'Vice', key: 'Vice' },
      { label: 'Gentrification', key: 'Gentrification' },
      { label: 'Nuisance', key: 'Nuisance' },
      { label: 'Superstition', key: 'Superstition' },
    ];

    for (const { label, key } of cases) {
      const switchEl = page.getByRole('switch', { name: label });
      const initiallyOn = (await switchEl.getAttribute('aria-checked')) === 'true';

      await switchEl.click();
      await expect(switchEl).toHaveAttribute('aria-checked', String(!initiallyOn));
      await expect.poll(() => isLayerOnMap(frame, key)).toBe(!initiallyOn);

      await switchEl.click();
      await expect(switchEl).toHaveAttribute('aria-checked', String(initiallyOn));
      await expect.poll(() => isLayerOnMap(frame, key)).toBe(initiallyOn);
    }
  });

  test('les 4 familles de cavaliers ont des markers à Lyon', async ({ page }) => {
    await page.goto('/');
    const frame = await getMapFrame(page);

    const counts = await frame.evaluate(() => {
      const byFamille = {};
      for (const entry of window.oracleCavalierMarkers || []) {
        byFamille[entry.famille] = (byFamille[entry.famille] || 0) + 1;
      }
      return byFamille;
    });

    for (const famille of ['vice', 'gentrification', 'nuisance', 'superstition']) {
      expect(counts[famille] || 0).toBeGreaterThan(0);
    }
  });

  test("la page ne déborde jamais verticalement, dans la vue Calques", async ({ page }) => {
    await page.goto('/');
    await goToCalques(page);

    const { scrollHeight, innerHeight } = await page.evaluate(() => ({
      scrollHeight: document.documentElement.scrollHeight,
      innerHeight: window.innerHeight,
    }));

    expect(scrollHeight).toBeLessThanOrEqual(innerHeight);
  });

  test('une seule légende est affichée sur la carte (plus de doublon avec l\'ancienne légende Folium)', async ({ page }) => {
    await page.goto('/');
    await getMapFrame(page);

    await expect(page.getByText('Légende', { exact: true })).toHaveCount(1);
  });

  test('avec Vice actif et un rayon de 300 m, les pings hors du cercle restent visibles (opacité >= 0.75)', async ({ page }) => {
    await page.goto('/');
    const frame = await getMapFrame(page);
    await scanQuartier(page, 'Ainay');
    await goToCalques(page);

    await page.getByRole('button', { name: '300 m', exact: true }).click();
    await frame.waitForFunction(() => Boolean(window.__oracleFocusCircle));

    const opacities = await frame.evaluate(() => {
      const center = window.__oracleFocusCircle.getLatLng();
      return (window.oracleCavalierMarkers || [])
        .filter((entry) => entry.famille === 'vice')
        .map((entry) => ({
          distM: center.distanceTo(L.latLng(entry.lat, entry.lng)),
          opacity: entry.m.options.opacity,
        }));
    });

    const outsideRadius = opacities.filter((o) => o.distM > 300);
    expect(outsideRadius.length).toBeGreaterThan(0);
    for (const o of outsideRadius) {
      expect(o.opacity).toBeGreaterThanOrEqual(0.75);
    }
  });

  test('le rayon "Aucun" supprime le cercle du rayon (CLEAR_FOCUS)', async ({ page }) => {
    await page.goto('/');
    const frame = await getMapFrame(page);
    await scanQuartier(page, 'Ainay');
    await goToCalques(page);

    await page.getByRole('button', { name: '300 m', exact: true }).click();
    await frame.waitForFunction(() => Boolean(window.__oracleFocusCircle));

    await page.getByRole('button', { name: 'Aucun', exact: true }).click();

    await frame.waitForFunction(() => !window.__oracleFocusCircle);
  });

  test('couper l\'interrupteur T2 retire les points T2 de la carte', async ({ page }) => {
    await page.goto('/');
    const frame = await getMapFrame(page);
    await goToCalques(page);

    const switchEl = page.getByRole('switch', { name: 'Apparts T2' });
    await expect(switchEl).toHaveAttribute('aria-checked', 'true');
    await expect.poll(() => isLayerOnMap(frame, 'T2')).toBe(true);

    await switchEl.click();

    await expect(switchEl).toHaveAttribute('aria-checked', 'false');
    await expect.poll(() => isLayerOnMap(frame, 'T2')).toBe(false);
  });
});
