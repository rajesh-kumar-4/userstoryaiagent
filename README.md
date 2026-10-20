# USERSTORYAI

USERSTORYAI is an enterprise platform that analyses change across the repositories in a workspace. It reports on branches, file churn, dependency and shared-tag relationships, risk scores, and release and pre-commit gates. It also supports Change Advisory Board (CAB) review, and it exports results to PDF, Excel, and JSON.

## Features: 

- Executive dashboard and CAB dashboard
- Repository discovery and branch comparison
- Change events with live refresh (polling)
- Risk heatmap and interactive dependency (shared-tag) graph
- Pre-commit validation and release gates
- Security findings view (SonarQube, Checkmarx, Sonatype, when configured)
- Dark mode, role-based access (VIEWER, ANALYST, ADMIN)
- Export to PDF, Excel, and JSON

## Repository layout

| Path | Purpose |
| --- | --- |
| `backend/` | FastAPI service: analysis, monitoring, security, RBAC, MCP endpoint |
| `frontend/` | React 19, Vite, TypeScript, Tailwind CSS v4, ShadCN-style UI |
| `k8s/` | Kubernetes manifests (Kustomize) |
| `docker-compose.yml` | Local full-stack run |
| `.github/workflows/` | CI and release pipelines |
| `docs/` | Setup, deployment, and architecture guides |

The `.github/` folder must sit at the root of the git repository. If your git root is the parent folder, move it there and adjust the `working-directory` values in the workflows.

## Quick start

With Docker:

```powershell
cd userstoryaiagent
copy .env.example .env      # set API_KEYS, WORKSPACE_DIR
docker compose up --build
```

Open http://localhost:8080. See [docs/SETUP.md](docs/SETUP.md) for local development and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Kubernetes.

## Documentation

- [Setup guide](docs/SETUP.md): local development, tests, configuration
- [Deployment guide](docs/DEPLOYMENT.md): Docker Compose, Kubernetes, secrets, scaling, TLS
- [Architecture](docs/ARCHITECTURE.md): layers, request flow, known limitations

## Status

Backend, frontend, RBAC, unit tests, and production frontend build are verified. Container images and Kubernetes manifests are written but have not been built or applied in this environment. See the limitations in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#known-limitations).
