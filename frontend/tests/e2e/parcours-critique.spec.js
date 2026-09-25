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

  // SearchForm est monté deux fois (colonne mobile masquée en CSS + panneau
  // desktop) : on ne cible que les éléments visibles.
  const visible = (locator) => locator.locator('visible=true');

  // Desktop : la vue par défaut est « Accueil », la recherche est dans la vue « Recherche ».
  await page.getByRole('button', { name: 'Lancer une recherche' }).click();

  // Saisie des critères : quartier (suggestion choisie, sinon la liste recouvre les
  // boutons de type de bien) + type de bien, puis lancement du scan.
  await visible(page.getByPlaceholder(/entrez un quartier/i)).fill('Gerland');
  await visible(page.getByRole('option', { name: /Gerland/ })).first().click();
  await visible(page.getByRole('button', { name: 'T2', exact: true })).click();
  await page.locator('form:visible button[type="submit"]').click();

  // Un résultat d'estimation réel (chiffré, avec son nombre de biens comparables) doit s'afficher.
  await expect(visible(page.getByText('Estimation Loyer')).first()).toBeVisible();
  await expect(visible(page.getByText(/^\d[\d\s]*$/)).first()).toBeVisible({ timeout: 15_000 });
  await expect(visible(page.getByText(/Basée sur \d+ biens comparables/))).toBeVisible();

  // Chatbot : sur desktop, vue « Immotep » du rail de navigation (la bulle flottante
  // « Ouvrir le chat Immotep » n'existe que sur mobile), puis envoi d'un message et
  // réception d'une réponse (le backend répond même sans GEMINI_API_KEY configuré,
  // avec un message explicite).
  await visible(page.getByRole('button', { name: /Immotep, chat disponible/ })).click();
  const chatInput = visible(page.getByPlaceholder('Prix, surface, quartier...'));
  await chatInput.fill('Bonjour Immotep');
  await visible(page.getByRole('button', { name: /envoyer le message/i })).click();

  // Messages du chat visible seulement : l'instance mobile (masquée) recopie l'historique,
  // donc le comptage global varie selon le timing (3 ou 4 constatés).
  const messages = visible(page.getByTestId('chat-message'));
  await expect(messages).toHaveCount(3, { timeout: 20_000 }); // accueil + user + réponse
  await expect(messages.nth(1)).toContainText('Bonjour Immotep');
  await expect(messages.nth(2)).not.toBeEmpty();
});
