/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Forward API calls to the backend (in Docker, nginx does this), so the family hub's login cookie is the page's own:
// port 8000 in development, API_PROXY in the browser tests
export default defineConfig({
  plugins: [react()],
  // The wall iPad's Safari may be older than 16.4: the built CSS must not use what it can't read, such as media range
  // syntax (width>=48rem), or md:hidden and the like silently stop working there. scripts/check-css.mjs checks it.
  build: { cssTarget: ['safari15'] },
  server: { proxy: { '/api': process.env.API_PROXY || 'http://localhost:8000' } },
  // The wall and the date logic are tested in the zone the family lives in
  test: { environment: 'jsdom', setupFiles: ['./src/testSetup.ts'], env: { TZ: 'Europe/Zurich' } },
})
