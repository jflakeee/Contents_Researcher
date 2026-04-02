import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: '.',
  baseURL: 'http://localhost:3000',
  use: { trace: 'on-first-retry' },
  webServer: {
    command: 'pnpm dev',
    port: 3000,
    reuseExistingServer: true,
  },
});
