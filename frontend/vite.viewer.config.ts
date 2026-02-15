import { resolve } from 'node:path'

import { defineConfig } from 'vite'

export default defineConfig({
  base: '/viewer-app/',
  build: {
    outDir: '../static/viewer-app',
    emptyOutDir: true,
    rollupOptions: {
      input: { index: resolve(__dirname, 'viewer.html') }
    }
  }
})
