import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// No Compose, API_PROXY_TARGET aponta para o serviço `api`.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    // Com a pasta montada do Windows no Docker, o Vite não recebe eventos de arquivo alterado.
    watch: { usePolling: process.env.VITE_USE_POLLING === 'true' },
    proxy: {
      // Back-end não tem prefixo /api (plano, seção 11): /api/health -> /health.
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
