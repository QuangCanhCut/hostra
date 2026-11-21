import { defineConfig } from '@playwright/test'

const chromeChannel =
  process.env.PW_CHANNEL || (process.platform === 'win32' ? 'chrome' : undefined)

export default defineConfig({
  testDir: './tests/e2e',
  outputDir: './test-artifacts/playwright-results',
  timeout: 45_000,
  retries: 0,
  use: {
    baseURL: 'http://127.0.0.1:4173',
    ...(chromeChannel ? { channel: chromeChannel } : {}),
    headless: true,
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
  webServer: {
    command: 'npm run preview -- --host 127.0.0.1 --port 4173',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: false,
    timeout: 30_000,
  },
})
