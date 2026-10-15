import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';

const local = (path: string) => fileURLToPath(new URL(path, import.meta.url));
export default defineConfig({
  root: local('./'),
  resolve: {
    alias: {
      'react-dom': local('./node_modules/react-dom'),
      'react': local('./node_modules/react'),
    },
  },
  esbuild: { jsx: 'automatic' },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: [local('./tests/setup.ts')],
    include: ['tests/**/*.test.{ts,tsx}'],
  },
});
