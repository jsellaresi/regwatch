import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  css: {
    preprocessorOptions: {
      scss: {
        // Use the modern Dart Sass compiler API (suppresses legacy-js-api warnings)
        api: 'modern-compiler',
      },
    },
  },
})
