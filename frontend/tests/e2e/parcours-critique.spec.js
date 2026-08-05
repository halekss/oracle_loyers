import { test, expect } from '@playwright/test';

// Parcours utilisateur critique (ORA-59), exécuté contre le build de
// production (voir playwright.config.js : webServer lance `npm run build`
// puis `vite preview`, avec un backend Flask réel — pas de mocks réseau) :
// saisie des critères -> résultat d'estimation affiché -> carte visible ->
// envoi d'un message au chatbot -> réception d'une réponse.

test('recherche, carte et chatbot fonctionnent de bout en bout', async ({ page }) => {
  await page.goto('/');

  // La carte est visible (iframe montée par défaut sur desktop).
  await expect(page.getByTitle('Carte Oracle')).toBeVisible();

  // Saisie des critères : quartier + type de bien.
  await page.getByPlaceholder(/entrez un quartier/i).fill('Gerland');
  await page.getByRole('button', { name: 'T2', exact: true }).click();

  // Un résultat d'estimation réel (chiffré) doit s'afficher.
  await expect(page.getByText('Estimation Loyer')).toBeVisible();
  await expect(page.getByText(/^\d[\d\s]*$/).first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/Données réelles \(\d+ biens\)/)).toBeVisible();

  // Chatbot : ouverture de la bulle flottante (le chat est un overlay
  // fermé par défaut, cf. App.jsx), puis envoi d'un message et réception
  // d'une réponse (le backend répond même sans GEMINI_API_KEY configuré,
  // avec un message explicite).
  await page.getByRole('button', { name: 'Ouvrir le chat Immotep' }).click();
  const chatInput = page.getByPlaceholder('Prix, surface, quartier...');
  await chatInput.fill('Bonjour Immotep');
  await page.getByRole('button', { name: /envoyer le message/i }).click();

  const messages = page.getByTestId('chat-message');
  await expect(messages).toHaveCount(3, { timeout: 20_000 }); // accueil + user + réponse
  await expect(messages.nth(1)).toContainText('Bonjour Immotep');
  await expect(messages.nth(2)).not.toBeEmpty();
});
