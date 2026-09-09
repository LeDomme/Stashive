# Stashive backend

The FastAPI backend is the API boundary for Stashive. The repository foundation only
contains configuration, database lifecycle infrastructure, and the health endpoint.

Run the development server from the repository root:

```bash
uv run --directory backend uvicorn app.main:app --reload --port 8000
```
