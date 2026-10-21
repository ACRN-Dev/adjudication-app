// vite.config.js
import { defineConfig } from "file:///C:/Automation/Adjudication%20app/node_modules/vite/dist/node/index.js";
import react from "file:///C:/Automation/Adjudication%20app/node_modules/@vitejs/plugin-react/dist/index.js";
import { fileURLToPath } from "node:url";
var __vite_injected_original_import_meta_url = "file:///C:/Automation/Adjudication%20app/vite.config.js";
var vite_config_default = defineConfig(({ command }) => {
  const demoUiEnabled = command === "serve" || process.env.VITE_ENABLE_DEMO_UI === "true";
  return {
    plugins: [react()],
    resolve: {
      alias: [{
        find: "./adminData",
        replacement: fileURLToPath(new URL(
          demoUiEnabled ? "./src/admin/adminData.js" : "./src/admin/adminData.production.js",
          __vite_injected_original_import_meta_url
        ))
      }]
    },
    server: {
      port: 5173,
      host: true,
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
          configure: (proxy) => {
            proxy.on("error", (_err, _req, res) => {
              if (!res.headersSent) {
                res.writeHead(503, { "Content-Type": "application/json" });
                res.end(JSON.stringify({
                  detail: "The backend API service is offline or unreachable on port 8000. Please start the backend service (npm run dev:api)."
                }));
              }
            });
          }
        }
      },
      watch: {
        // Ignore docx, xlsx, and non-code folders to prevent OneDrive file lock watcher crashes
        ignored: [
          "**/*.docx",
          "**/*.xlsx",
          "**/*.pdf",
          "**/Supporting SOPs/**",
          "**/Prompts and workflow/**",
          "**/Suggested architecture/**"
        ]
      }
    }
  };
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJDOlxcXFxBdXRvbWF0aW9uXFxcXEFkanVkaWNhdGlvbiBhcHBcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkM6XFxcXEF1dG9tYXRpb25cXFxcQWRqdWRpY2F0aW9uIGFwcFxcXFx2aXRlLmNvbmZpZy5qc1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vQzovQXV0b21hdGlvbi9BZGp1ZGljYXRpb24lMjBhcHAvdml0ZS5jb25maWcuanNcIjtpbXBvcnQgeyBkZWZpbmVDb25maWcgfSBmcm9tICd2aXRlJ1xyXG5pbXBvcnQgcmVhY3QgZnJvbSAnQHZpdGVqcy9wbHVnaW4tcmVhY3QnXHJcbmltcG9ydCB7IGZpbGVVUkxUb1BhdGggfSBmcm9tICdub2RlOnVybCdcclxuXHJcbi8vIGh0dHBzOi8vdml0ZWpzLmRldi9jb25maWcvXHJcbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZygoeyBjb21tYW5kIH0pID0+IHtcclxuICBjb25zdCBkZW1vVWlFbmFibGVkID0gY29tbWFuZCA9PT0gJ3NlcnZlJyB8fCBwcm9jZXNzLmVudi5WSVRFX0VOQUJMRV9ERU1PX1VJID09PSAndHJ1ZSc7XHJcbiAgcmV0dXJuIHtcclxuICAgIHBsdWdpbnM6IFtyZWFjdCgpXSxcclxuICAgIHJlc29sdmU6IHtcclxuICAgICAgYWxpYXM6IFt7XHJcbiAgICAgICAgZmluZDogJy4vYWRtaW5EYXRhJyxcclxuICAgICAgICByZXBsYWNlbWVudDogZmlsZVVSTFRvUGF0aChuZXcgVVJMKFxyXG4gICAgICAgICAgZGVtb1VpRW5hYmxlZCA/ICcuL3NyYy9hZG1pbi9hZG1pbkRhdGEuanMnIDogJy4vc3JjL2FkbWluL2FkbWluRGF0YS5wcm9kdWN0aW9uLmpzJyxcclxuICAgICAgICAgIGltcG9ydC5tZXRhLnVybFxyXG4gICAgICAgICkpXHJcbiAgICAgIH1dXHJcbiAgICB9LFxyXG4gICAgc2VydmVyOiB7XHJcbiAgICAgIHBvcnQ6IDUxNzMsXHJcbiAgICAgIGhvc3Q6IHRydWUsXHJcbiAgICAgIHByb3h5OiB7XHJcbiAgICAgICAgJy9hcGknOiB7XHJcbiAgICAgICAgICB0YXJnZXQ6ICdodHRwOi8vMTI3LjAuMC4xOjgwMDAnLFxyXG4gICAgICAgICAgY2hhbmdlT3JpZ2luOiB0cnVlLFxyXG4gICAgICAgICAgY29uZmlndXJlOiAocHJveHkpID0+IHtcclxuICAgICAgICAgICAgcHJveHkub24oJ2Vycm9yJywgKF9lcnIsIF9yZXEsIHJlcykgPT4ge1xyXG4gICAgICAgICAgICAgIGlmICghcmVzLmhlYWRlcnNTZW50KSB7XHJcbiAgICAgICAgICAgICAgICByZXMud3JpdGVIZWFkKDUwMywgeyAnQ29udGVudC1UeXBlJzogJ2FwcGxpY2F0aW9uL2pzb24nIH0pO1xyXG4gICAgICAgICAgICAgICAgcmVzLmVuZChKU09OLnN0cmluZ2lmeSh7XHJcbiAgICAgICAgICAgICAgICAgIGRldGFpbDogJ1RoZSBiYWNrZW5kIEFQSSBzZXJ2aWNlIGlzIG9mZmxpbmUgb3IgdW5yZWFjaGFibGUgb24gcG9ydCA4MDAwLiBQbGVhc2Ugc3RhcnQgdGhlIGJhY2tlbmQgc2VydmljZSAobnBtIHJ1biBkZXY6YXBpKS4nXHJcbiAgICAgICAgICAgICAgICB9KSk7XHJcbiAgICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICB9KTtcclxuICAgICAgICAgIH1cclxuICAgICAgICB9XHJcbiAgICAgIH0sXHJcbiAgICAgIHdhdGNoOiB7XHJcbiAgICAgICAgLy8gSWdub3JlIGRvY3gsIHhsc3gsIGFuZCBub24tY29kZSBmb2xkZXJzIHRvIHByZXZlbnQgT25lRHJpdmUgZmlsZSBsb2NrIHdhdGNoZXIgY3Jhc2hlc1xyXG4gICAgICAgIGlnbm9yZWQ6IFtcclxuICAgICAgICAgICcqKi8qLmRvY3gnLFxyXG4gICAgICAgICAgJyoqLyoueGxzeCcsXHJcbiAgICAgICAgICAnKiovKi5wZGYnLFxyXG4gICAgICAgICAgJyoqL1N1cHBvcnRpbmcgU09Qcy8qKicsXHJcbiAgICAgICAgICAnKiovUHJvbXB0cyBhbmQgd29ya2Zsb3cvKionLFxyXG4gICAgICAgICAgJyoqL1N1Z2dlc3RlZCBhcmNoaXRlY3R1cmUvKionXHJcbiAgICAgICAgXVxyXG4gICAgICB9XHJcbiAgICB9XHJcbiAgfTtcclxufSlcclxuIl0sCiAgIm1hcHBpbmdzIjogIjtBQUFvUixTQUFTLG9CQUFvQjtBQUNqVCxPQUFPLFdBQVc7QUFDbEIsU0FBUyxxQkFBcUI7QUFGMkksSUFBTSwyQ0FBMkM7QUFLMU4sSUFBTyxzQkFBUSxhQUFhLENBQUMsRUFBRSxRQUFRLE1BQU07QUFDM0MsUUFBTSxnQkFBZ0IsWUFBWSxXQUFXLFFBQVEsSUFBSSx3QkFBd0I7QUFDakYsU0FBTztBQUFBLElBQ0wsU0FBUyxDQUFDLE1BQU0sQ0FBQztBQUFBLElBQ2pCLFNBQVM7QUFBQSxNQUNQLE9BQU8sQ0FBQztBQUFBLFFBQ04sTUFBTTtBQUFBLFFBQ04sYUFBYSxjQUFjLElBQUk7QUFBQSxVQUM3QixnQkFBZ0IsNkJBQTZCO0FBQUEsVUFDN0M7QUFBQSxRQUNGLENBQUM7QUFBQSxNQUNILENBQUM7QUFBQSxJQUNIO0FBQUEsSUFDQSxRQUFRO0FBQUEsTUFDTixNQUFNO0FBQUEsTUFDTixNQUFNO0FBQUEsTUFDTixPQUFPO0FBQUEsUUFDTCxRQUFRO0FBQUEsVUFDTixRQUFRO0FBQUEsVUFDUixjQUFjO0FBQUEsVUFDZCxXQUFXLENBQUMsVUFBVTtBQUNwQixrQkFBTSxHQUFHLFNBQVMsQ0FBQyxNQUFNLE1BQU0sUUFBUTtBQUNyQyxrQkFBSSxDQUFDLElBQUksYUFBYTtBQUNwQixvQkFBSSxVQUFVLEtBQUssRUFBRSxnQkFBZ0IsbUJBQW1CLENBQUM7QUFDekQsb0JBQUksSUFBSSxLQUFLLFVBQVU7QUFBQSxrQkFDckIsUUFBUTtBQUFBLGdCQUNWLENBQUMsQ0FBQztBQUFBLGNBQ0o7QUFBQSxZQUNGLENBQUM7QUFBQSxVQUNIO0FBQUEsUUFDRjtBQUFBLE1BQ0Y7QUFBQSxNQUNBLE9BQU87QUFBQTtBQUFBLFFBRUwsU0FBUztBQUFBLFVBQ1A7QUFBQSxVQUNBO0FBQUEsVUFDQTtBQUFBLFVBQ0E7QUFBQSxVQUNBO0FBQUEsVUFDQTtBQUFBLFFBQ0Y7QUFBQSxNQUNGO0FBQUEsSUFDRjtBQUFBLEVBQ0Y7QUFDRixDQUFDOyIsCiAgIm5hbWVzIjogW10KfQo=
