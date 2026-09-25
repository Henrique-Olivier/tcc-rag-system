import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// No Compose, API_PROXY_TARGET aponta para o serviço `api`.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Back-end não tem prefixo /api (plano, seção 8): /api/health -> /health.
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
