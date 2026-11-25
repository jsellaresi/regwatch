import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// `npm run dev` outside Docker has no nginx in front, so forward API calls to the backend.
const API = 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/analyze': API,
      '/chat': API,
      '/resume': API,
      '/state': API,
      '/ingest': API,
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        // Use the modern Dart Sass compiler API (suppresses legacy-js-api warnings)
        api: 'modern-compiler',
      },
    },
  },
})
