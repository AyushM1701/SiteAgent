import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: path.resolve(__dirname, '../web_ui_static'),
    emptyOutDir: false, // Prevents deleting the backup index.monolith.html.bak
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/preview': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/shell': {
        target: 'ws://127.0.0.1:5001',
        ws: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:5002',
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
