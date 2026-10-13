import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig(({ command }) => {
  const demoUiEnabled = command === 'serve' || process.env.VITE_ENABLE_DEMO_UI === 'true';
  return {
    plugins: [react()],
    resolve: {
      alias: [{
        find: './adminData',
        replacement: fileURLToPath(new URL(
          demoUiEnabled ? './src/admin/adminData.js' : './src/admin/adminData.production.js',
          import.meta.url
        ))
      }]
    },
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
  };
})
