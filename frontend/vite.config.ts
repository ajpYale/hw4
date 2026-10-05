import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// /api and /static are proxied to the FastAPI backend so the image paths the
// database hands back ("/static/products/foo.jpg") work unchanged in the browser.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/static': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
