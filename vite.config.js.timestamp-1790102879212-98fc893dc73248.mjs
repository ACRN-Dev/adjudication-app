// vite.config.js
import { defineConfig } from "file:///C:/Automation/Adjudication%20app/node_modules/vite/dist/node/index.js";
import react from "file:///C:/Automation/Adjudication%20app/node_modules/@vitejs/plugin-react/dist/index.js";
var vite_config_default = defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true
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
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJDOlxcXFxBdXRvbWF0aW9uXFxcXEFkanVkaWNhdGlvbiBhcHBcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkM6XFxcXEF1dG9tYXRpb25cXFxcQWRqdWRpY2F0aW9uIGFwcFxcXFx2aXRlLmNvbmZpZy5qc1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vQzovQXV0b21hdGlvbi9BZGp1ZGljYXRpb24lMjBhcHAvdml0ZS5jb25maWcuanNcIjtpbXBvcnQgeyBkZWZpbmVDb25maWcgfSBmcm9tICd2aXRlJ1xyXG5pbXBvcnQgcmVhY3QgZnJvbSAnQHZpdGVqcy9wbHVnaW4tcmVhY3QnXHJcblxyXG4vLyBodHRwczovL3ZpdGVqcy5kZXYvY29uZmlnL1xyXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xyXG4gIHBsdWdpbnM6IFtyZWFjdCgpXSxcclxuICBzZXJ2ZXI6IHtcclxuICAgIHBvcnQ6IDUxNzMsXHJcbiAgICBob3N0OiB0cnVlLFxyXG4gICAgcHJveHk6IHtcclxuICAgICAgJy9hcGknOiB7XHJcbiAgICAgICAgdGFyZ2V0OiAnaHR0cDovLzEyNy4wLjAuMTo4MDAwJyxcclxuICAgICAgICBjaGFuZ2VPcmlnaW46IHRydWVcclxuICAgICAgfVxyXG4gICAgfSxcclxuICAgIHdhdGNoOiB7XHJcbiAgICAgIC8vIElnbm9yZSBkb2N4LCB4bHN4LCBhbmQgbm9uLWNvZGUgZm9sZGVycyB0byBwcmV2ZW50IE9uZURyaXZlIGZpbGUgbG9jayB3YXRjaGVyIGNyYXNoZXNcclxuICAgICAgaWdub3JlZDogW1xyXG4gICAgICAgICcqKi8qLmRvY3gnLFxyXG4gICAgICAgICcqKi8qLnhsc3gnLFxyXG4gICAgICAgICcqKi8qLnBkZicsXHJcbiAgICAgICAgJyoqL1N1cHBvcnRpbmcgU09Qcy8qKicsXHJcbiAgICAgICAgJyoqL1Byb21wdHMgYW5kIHdvcmtmbG93LyoqJyxcclxuICAgICAgICAnKiovU3VnZ2VzdGVkIGFyY2hpdGVjdHVyZS8qKidcclxuICAgICAgXVxyXG4gICAgfVxyXG4gIH1cclxufSlcclxuIl0sCiAgIm1hcHBpbmdzIjogIjtBQUFvUixTQUFTLG9CQUFvQjtBQUNqVCxPQUFPLFdBQVc7QUFHbEIsSUFBTyxzQkFBUSxhQUFhO0FBQUEsRUFDMUIsU0FBUyxDQUFDLE1BQU0sQ0FBQztBQUFBLEVBQ2pCLFFBQVE7QUFBQSxJQUNOLE1BQU07QUFBQSxJQUNOLE1BQU07QUFBQSxJQUNOLE9BQU87QUFBQSxNQUNMLFFBQVE7QUFBQSxRQUNOLFFBQVE7QUFBQSxRQUNSLGNBQWM7QUFBQSxNQUNoQjtBQUFBLElBQ0Y7QUFBQSxJQUNBLE9BQU87QUFBQTtBQUFBLE1BRUwsU0FBUztBQUFBLFFBQ1A7QUFBQSxRQUNBO0FBQUEsUUFDQTtBQUFBLFFBQ0E7QUFBQSxRQUNBO0FBQUEsUUFDQTtBQUFBLE1BQ0Y7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUNGLENBQUM7IiwKICAibmFtZXMiOiBbXQp9Cg==
