import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (_err, _req, res) => {
            if (!res.headersSent) {
              res.writeHead(503, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({
                detail: 'The backend API service is offline or unreachable on port 8000. Please start the backend service (npm run dev:api).'
              }));
            }
          });
        }
      }
    },
    watch: {
      // Ignore docx, xlsx, and non-code folders to prevent OneDrive file lock watcher crashes
      ignored: [
        '**/*.docx',
        '**/*.xlsx',
        '**/*.pdf',
        '**/Supporting SOPs/**',
        '**/Prompts and workflow/**',
        '**/Suggested architecture/**'
      ]
    }
  }
})
