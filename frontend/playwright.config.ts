import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://127.0.0.1:5173' },
  webServer: [
    { command: 'cd ../backend && rm -f /tmp/stashive-auth-e2e.db && APP_ENVIRONMENT=test AUTH_TEST_SETUP_TOKEN=e2e-setup-token DATABASE_URL=sqlite:////tmp/stashive-auth-e2e.db uv run alembic upgrade head && APP_ENVIRONMENT=test AUTH_TEST_SETUP_TOKEN=e2e-setup-token DATABASE_URL=sqlite:////tmp/stashive-auth-e2e.db uv run uvicorn app.main:app --host 127.0.0.1 --port 8000', url: 'http://127.0.0.1:8000/api/auth/status', reuseExistingServer: false },
    { command: 'npm run dev -- --host 127.0.0.1', url: 'http://127.0.0.1:5173', reuseExistingServer: false },
  ],
})
