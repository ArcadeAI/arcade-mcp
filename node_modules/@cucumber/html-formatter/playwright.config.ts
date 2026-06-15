import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './test',
  fullyParallel: true,
  webServer: {
    command: 'npx serve ./test/__output__',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    stdout: 'ignore',
    stderr: 'pipe',
  },
  use: {
    headless: true,
    baseURL: 'http://localhost:3000',
    colorScheme: 'light',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
  snapshotPathTemplate: '{testDir}/__screenshots__/{arg}{ext}',
  expect: {
    toHaveScreenshot: {
      stylePath: './test/screenshot.css',
    },
  },
})
