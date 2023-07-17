import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 9235,
    proxy: {
      '/api': {
        target: 'http://192.168.100.27:8000/',
        changeOrigin: true,
        ws: true,
        pathRewrite: {
          '^/api': '',
        },
      },
      '/tasks': {
        target: 'http://192.168.100.27:8000/tasks/',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/tasks/, '')
      }
    },
  },
})
