import '@testing-library/jest-dom/vitest';

// jsdom n'implémente pas scrollIntoView ; plusieurs composants (ChatOracle...)
// l'appellent sur chaque nouveau message.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

// Node 22+ expose un `localStorage` natif (Web Storage API), backé par un
// fichier (--localstorage-file) : dans ce process de test (vitest, workers
// sans chemin de fichier valide), il masque le Storage de jsdom par un objet
// inerte (sans .clear/.getItem/.setItem...), qui fait échouer tout test
// appelant `localStorage.clear()` en beforeEach — pré-existant à toute
// fonctionnalité de l'app. Polyfill mémoire minimal, seulement si
// l'implémentation exposée est cassée.
if (typeof localStorage === 'undefined' || typeof localStorage.clear !== 'function') {
  class MemoryStorage {
    #store = new Map();
    get length() {
      return this.#store.size;
    }
    clear() {
      this.#store.clear();
    }
    getItem(key) {
      return this.#store.has(key) ? this.#store.get(key) : null;
    }
    setItem(key, value) {
      this.#store.set(key, String(value));
    }
    removeItem(key) {
      this.#store.delete(key);
    }
    key(index) {
      return Array.from(this.#store.keys())[index] ?? null;
    }
  }
  const memoryStorage = new MemoryStorage();
  Object.defineProperty(globalThis, 'localStorage', { value: memoryStorage, configurable: true, writable: true });
  Object.defineProperty(window, 'localStorage', { value: memoryStorage, configurable: true, writable: true });
}
