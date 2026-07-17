import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const coordinatorTarget = 'http://localhost:5000';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: coordinatorTarget,
        changeOrigin: true,
        ws: true
      },
      '/ws': {
        target: coordinatorTarget,
        changeOrigin: true,
        ws: true
      },
      '/health': {
        target: coordinatorTarget,
        changeOrigin: true,
        ws: true
      }
    }
  }
});
