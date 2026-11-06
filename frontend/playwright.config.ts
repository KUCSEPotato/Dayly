import { defineConfig, devices } from '@playwright/test'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontend = dirname(fileURLToPath(import.meta.url))
// Supply only an isolated test instance here; these tests create and delete tasks.
const externalBaseUrl = process.env.E2E_BASE_URL
const database = externalBaseUrl ? '' : join(mkdtempSync(join(tmpdir(), 'dayly-e2e-')), 'test.db')

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: externalBaseUrl ?? 'http://127.0.0.1:5174', trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: externalBaseUrl ? undefined : [
    {
      command: '.venv/bin/alembic upgrade head && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001',
      cwd: resolve(frontend, '../backend'),
      env: { DATABASE_URL: `sqlite:///${database}` },
      url: 'http://127.0.0.1:8001/openapi.json',
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --port 5174',
      env: { API_PROXY_TARGET: 'http://127.0.0.1:8001' },
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
    },
  ],
})
