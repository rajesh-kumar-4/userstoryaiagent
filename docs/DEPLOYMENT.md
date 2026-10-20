# Deployment guide

This guide covers production-style deployment with Docker Compose and Kubernetes. Read the [known limitations](ARCHITECTURE.md#known-limitations) before going live.

## Images

| Image | Source | Base | Runs as | Port |
| --- | --- | --- | --- | --- |
| `userstoryai/backend:0.4.0` | `backend/Dockerfile` | `python:3.12-slim` | UID 10001 | 8000 |
| `userstoryai/frontend:0.4.0` | `frontend/Dockerfile` | `nginxinc/nginx-unprivileged:1.27-alpine` | UID 101 | 8080 |

The backend image includes the git CLI. Both images use a read-only root filesystem with writable `/tmp`. The frontend nginx config adds security headers and a Content Security Policy.

Build both images locally:

```powershell
docker build -t userstoryai/backend:0.4.0 userstoryaiagent\backend
docker build -t userstoryai/frontend:0.4.0 userstoryaiagent\frontend
```

The release workflow publishes `ghcr.io/<owner>/userstoryai-backend` and `ghcr.io/<owner>/userstoryai-frontend` when a `v*` tag is pushed.

## Option A: Docker Compose

Suitable for a single host.

1. Copy `userstoryaiagent\.env.example` to `userstoryaiagent\.env`.
2. Set `API_KEYS` to a JSON object with long random keys, for example `'{"<random-key>":"ADMIN"}'`.
3. Set `WORKSPACE_DIR` to the folder that holds the repositories.
4. Start the stack:

```powershell
cd userstoryaiagent
docker compose up -d --build
docker compose ps
```

The frontend waits for the backend health check before starting. Compose publishes the UI on `FRONTEND_PORT` (default 8080). Put a reverse proxy with TLS in front of it for any non-local use.

The backend service is hardened with `read_only`, `cap_drop: ALL`, `no-new-privileges`, and a `tmpfs` for `/tmp`.

## Option B: Kubernetes

Requirements:

- An NGINX ingress controller (`ingressClassName: nginx`)
- metrics-server (required by the frontend HPA)
- A `ReadWriteMany` storage class for the workspace volume
- A TLS secret named `userstoryai-tls`, or cert-manager configured for the ingress

### 1. Set the placeholders

- `k8s/workspace-pvc.yaml`: replace `REPLACE_WITH_RWX_STORAGE_CLASS`.
- `k8s/ingress.yaml`: replace `userstoryai.example.com` with your host.
- `k8s/kustomization.yaml`: point the images at your registry, for example:

```yaml
images:
  - name: userstoryai/backend
    newName: ghcr.io/your-org/userstoryai-backend
    newTag: 0.4.0
  - name: userstoryai/frontend
    newName: ghcr.io/your-org/userstoryai-frontend
    newTag: 0.4.0
```

### 2. Create the secret

Do not commit real keys. `k8s/secret.example.yaml` is an example only and is not in the kustomization.

Create the namespace, then write the JSON to a local file outside the repository and create the secret from it:

```powershell
kubectl create namespace userstoryai
Set-Content -Path "$env:TEMP\api-keys.json" -Value '{"<random-key>":"ADMIN"}'
kubectl -n userstoryai create secret generic userstoryai-secrets "--from-file=API_KEYS=$env:TEMP\api-keys.json"
Remove-Item "$env:TEMP\api-keys.json"
```

In production, use your secret manager (Sealed Secrets, External Secrets, or Vault) instead.

### 3. Populate the workspace

The backend mounts `userstoryai-workspace` read-only at `/workspace`. The manifests do not clone repositories. Populate the claim with your own process, such as a git-sync sidecar or a CronJob, before or after deployment. Until it contains repositories, the dashboards are empty.

### 4. Apply

```powershell
kubectl apply -k userstoryaiagent\k8s
kubectl -n userstoryai rollout status deploy/backend
kubectl -n userstoryai rollout status deploy/frontend
```

Check the ingress and open the host in a browser. Test the API through the UI: `https://<host>/api/health`.

## Scaling and availability

- **Backend: one replica only.** Event history, analysis history, and monitor state are in memory. The deployment uses `replicas: 1` and `strategy: Recreate`. A restart clears in-memory history.
- **Frontend: 2 to 6 replicas** through `frontend-hpa.yaml`, scaling on 70% average CPU. The frontend is stateless.
- The frontend proxies `/api/` to the `backend` Service. The service name must stay `backend` in both Compose and Kubernetes.

## Configuration reference

Backend variables. Field names are upper-cased for environment variables.

| Variable | Default | Purpose |
| --- | --- | --- |
| `WORKSPACE_ROOT` | parent of platform folder | Repositories to analyse |
| `MAX_DISCOVERY_DEPTH` | `2` | Folder depth searched for repositories (1 to 8) |
| `MONITOR_MODE` | `MANUAL` | Change monitoring mode |
| `MONITOR_INTERVAL_SECONDS` | `30` | Polling interval for the monitor |
| `EVENT_HISTORY_SIZE` | `500` | In-memory change event history |
| `ANALYSIS_HISTORY_SIZE` | `1000` | In-memory analysis history |
| `LOG_LEVEL` | `INFO` | Logging level |
| `AUTH_ENABLED` | `false` | Enforce `X-API-Key` authentication. Set `true` in deployments |
| `API_KEYS` | `{}` | JSON object of key to role (`VIEWER`, `ANALYST`, `ADMIN`) |
| `LLM_PROVIDER` | `none` | `none`, `openai`, `azure_openai`, `ollama`, or `generative_engine` |
| `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_TIMEOUT_SECONDS` | unset | LLM provider settings |
| `LLM_AZURE_DEPLOYMENT`, `LLM_AZURE_API_VERSION` | unset, `2024-06-01` | Azure OpenAI settings |
| `SONARQUBE_URL`, `SONARQUBE_TOKEN` | unset | SonarQube integration (enabled when both are set) |
| `CHECKMARX_URL`, `CHECKMARX_IAM_URL`, `CHECKMARX_TENANT`, `CHECKMARX_REFRESH_TOKEN` | unset | Checkmarx integration (contract not verified, see limitations) |
| `SONATYPE_URL`, `SONATYPE_USERNAME`, `SONATYPE_TOKEN` | unset | Sonatype integration (contract not verified) |
| `SECURITY_TIMEOUT_SECONDS` | `10` | Timeout for scanner calls |
| `TELEMETRY_ENABLED` | `false` | OpenTelemetry export |
| `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT` | `userstoryai-platform`, unset | OpenTelemetry settings |

Roles:

| Role | Access |
| --- | --- |
| `VIEWER` | Read dashboards and reports |
| `ANALYST` | Viewer rights plus analysis runs |
| `ADMIN` | All operations |

Requests send the key in the `X-API-Key` header. `GET /health` does not require a key.

## TLS

- Compose: terminate TLS at a reverse proxy (Caddy, Traefik, or an external load balancer) in front of port 8080.
- Kubernetes: create `userstoryai-tls` with cert-manager or a certificate you manage. The ingress already references it.

## Verification after deployment

```powershell
kubectl -n userstoryai get pods,svc,ingress,hpa
curl -fsS https://<host>/healthz
curl -fsS https://<host>/api/health
```

## Known limitations

- Live updates use polling (every 15 seconds in the UI), not push.
- Single backend replica, because state is in memory.
- No AST or dependency-graph API. The UI shows shared-tag and file-level views.
- Checkmarx and Sonatype integration contracts are not verified against live services.
- The Python 3.12 container target is not verified in this environment. Docker was not available, so no images were built here.
- The nginx Content Security Policy has not been checked against runtime behaviour in a browser.
- The workspace mount is read-only. Git read operations are expected to work, but this is not verified.
