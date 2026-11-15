import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Tudo que começa com /api vai para o backend Python (python app.py)
    proxy: {
      '/api': 'http://127.0.0.1:5000',
    },
  },
})
