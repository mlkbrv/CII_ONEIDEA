import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev server proxies API calls to the FastAPI backend on :8000, so the
// frontend uses relative URLs and never deals with CORS in development.
// Served by FastAPI under /admin-ui/, so asset URLs must carry that prefix.
export default defineConfig({
  base: '/admin-ui/',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})