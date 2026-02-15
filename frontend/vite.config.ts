import { defineConfig } from 'vite'

export default defineConfig({
  base: '/home-app/',
  build: {
    outDir: '../static/home-app',
    emptyOutDir: true
  }
})
