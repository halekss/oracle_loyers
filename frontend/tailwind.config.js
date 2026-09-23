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
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Archivo', 'Inter', 'ui-sans-serif', 'sans-serif'],
      },
    },
  },
  plugins: [],
}