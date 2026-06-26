import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const allowedHosts = ['oracle-loyers.onrender.com']

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts,
  },
  preview: {
    allowedHosts,
  },
})
