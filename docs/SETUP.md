# Setup guide

This guide covers running USERSTORYAI on a developer machine. Python 3.12 and Node.js 24 are the versions used in CI and in the container images. The commands below use Windows PowerShell 5.1, and macOS or Linux shells work the same way with the activation command changed.

## Prerequisites

- Python 3.12 or later
- Node.js 24 and npm 11
- Git on `PATH` (the backend reads repositories through the git CLI)
- Docker Desktop or Docker Engine with Compose v2 (optional, for container runs)

## Backend: 

```powershell
cd userstoryaiagent\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Check the service:

```powershell
curl http://localhost:8000/health
```

Configuration is read from environment variables and from a `.env` file in the directory you start the server from. For local work, the defaults are enough:

| Variable | Default | Notes |
| --- | --- | --- |
| `WORKSPACE_ROOT` | parent of `userstoryaiagent` | Folder that contains the repositories to analyse |
| `AUTH_ENABLED` | `false` | When false, every request runs as ADMIN. Keep `true` outside a laptop |
| `API_KEYS` | `{}` | JSON object of key to role, for example `{"dev-key":"ADMIN"}` |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `LLM_PROVIDER` | `none` | `none` uses rule-based summaries |

See [DEPLOYMENT.md](DEPLOYMENT.md#configuration-reference) for the full list.

## Frontend

```powershell
cd userstoryaiagent\frontend
npm ci
npm run dev
```

Open the URL that Vite prints (usually http://localhost:5173). The dev server proxies `/api/*` to the backend and strips the prefix. The target defaults to `http://localhost:8000`. To change it, create `frontend\.env.local` from `frontend\.env.example`:

```
VITE_BACKEND_PROXY_TARGET=http://localhost:8000
```

When `AUTH_ENABLED=true`, click **Set API key** in the top bar and enter a key from `API_KEYS`. The key is stored in the browser's local storage and sent as the `X-API-Key` header.

## Tests and checks

Backend:

```powershell
cd userstoryaiagent\backend
python -m pytest
```

Frontend:

```powershell
cd userstoryaiagent\frontend
npm run typecheck
npm test
npm run build
npm audit --omit=dev --audit-level=high
```

`npm run build` runs the typecheck first, then produces the static bundle in `dist/`.

## Local containers

```powershell
cd userstoryaiagent
copy .env.example .env
notepad .env          # set API_KEYS and WORKSPACE_DIR
docker compose up --build
```

- UI: http://localhost:8080
- API through the UI proxy: http://localhost:8080/api/health

`WORKSPACE_DIR` is a host folder. It is mounted read-only at `/workspace` in the backend container. It defaults to the parent folder of `userstoryaiagent`.

Stop the stack with `docker compose down`.

## Troubleshooting

| Symptom | Likely cause and fix |
| --- | --- |
| `401` or `403` in the UI | API key missing or not in `API_KEYS`. Use **Set API key** in the top bar with a valid key |
| UI shows the backend as unreachable | Backend not running, or `VITE_BACKEND_PROXY_TARGET` points to the wrong port |
| No repositories listed | `WORKSPACE_ROOT` does not contain git repositories within `MAX_DISCOVERY_DEPTH` (default 2) |
| Git operations fail in a container | The mounted folder is owned by another user. Git is configured with `safe.directory=*` in the image, and the mount is read-only |
| `docker compose up` fails with `API_KEYS` error | `.env` is missing or `API_KEYS` is not set |
