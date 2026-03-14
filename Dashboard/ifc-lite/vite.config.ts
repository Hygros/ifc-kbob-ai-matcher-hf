import { defineConfig, type ViteDevServer } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const packageJsonPath = new URL('./package.json', import.meta.url);
const pkg = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

export default defineConfig({
  base: './',
  plugins: [
    react(),
    {
      name: 'wasm-mime-type',
      configureServer(server: ViteDevServer) {
        server.middlewares.use((
          req: { url?: string },
          res: { setHeader: (name: string, value: string) => void },
          next: () => void,
        ) => {
          if (req.url?.endsWith('.wasm')) {
            res.setHeader('Content-Type', 'application/wasm');
          }
          next();
        });
      },
    },
  ],
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
    __BUILD_DATE__: JSON.stringify(new Date().toISOString()),
    __RELEASE_HISTORY__: JSON.stringify([]),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    open: false,
    fs: {
      allow: ['..'],
    },
  },
  build: {
    target: 'esnext',
  },
  optimizeDeps: {
    exclude: ['@duckdb/duckdb-wasm', '@ifc-lite/wasm'],
  },
  assetsInclude: ['**/*.wasm'],
});
