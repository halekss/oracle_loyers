/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // ORA-170 : tokens du design system "carte sombre" (artefact Claude
      // Design « Oracle des Loyers — Refonte », socle commun ORA-163).
      colors: {
        ink: {
          950: '#070a12',
          900: '#151c33',
          800: '#232b45',
          700: '#1e2a48',
          DEFAULT: '#f1f5f9',
          muted: '#94a3b8',
          dim: '#8b93a7',
        },
        market: { below: '#22c55e', within: '#facc15', above: '#e9003a' },
        accent: { DEFAULT: '#7c3aed', light: '#a78bfa' },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Archivo', 'Inter', 'ui-sans-serif', 'sans-serif'],
      },
    },
  },
  plugins: [],
}