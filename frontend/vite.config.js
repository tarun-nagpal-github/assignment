import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/search': 'http://localhost:8000',
      '/tags': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/regions': 'http://localhost:8000',
    },
  },
})
