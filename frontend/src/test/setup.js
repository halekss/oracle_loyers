import '@testing-library/jest-dom/vitest';

// jsdom n'implémente pas scrollIntoView ; plusieurs composants (ChatOracle...)
// l'appellent sur chaque nouveau message.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
