from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes_agents import router as agents_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_intelligence import router as intelligence_router
from app.api.routes_monitoring import router as monitoring_router
from app.api.routes_repositories import router as repositories_router
from app.api.routes_system import router as system_router
from app.config import Settings, get_settings
from app.container import build_container
from app.core.exceptions import DomainError
from app.core.logging import setup_logging
from app.core.telemetry import configure_telemetry
from app.mcp.repository_tools import register_repository_tools
from app.rag.tools import register_rag_tools

API_VERSION = "0.5.0"

OPENAPI_TAGS = [
    {"name": "system", "description": "Health and MCP endpoint."},
    {"name": "repositories", "description": "Repository discovery, git metadata, and history."},
    {"name": "intelligence", "description": "Change scope and workspace summary."},
    {"name": "monitoring", "description": "Workspace monitor and change events."},
    {"name": "analysis", "description": "Change-risk analysis for commits, branches, PRs, and releases."},
    {"name": "dashboard", "description": "Portfolio risk summary, per-repository risk, and trends."},
    {"name": "agents", "description": "Ten-agent workflow: catalog, runs, and run lookup."},
    {"name": "rag", "description": "Retrieval over indexed historical records and agent outputs."},
]


async def _domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc), "error": type(exc).__name__})


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)
    configure_telemetry(settings)
    container = build_container(settings)
    register_repository_tools(container.tool_registry(), container)
    register_rag_tools(container.tool_registry(), container)
    container.agent_workflow()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container.registry().refresh()
        monitor = container.monitor()
        await monitor.start()
        try:
            yield
        finally:
            await monitor.stop()
            container.vector_store().close()

    app = FastAPI(
        title="UserStoryAI Repository Intelligence",
        version=API_VERSION,
        description="Repository intelligence, change-risk analysis, and AI-assisted reporting.",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.container = container
    app.add_exception_handler(DomainError, _domain_error_handler)
    app.include_router(system_router)
    app.include_router(repositories_router)
    app.include_router(intelligence_router)
    app.include_router(monitoring_router)
    app.include_router(analysis_router)
    app.include_router(dashboard_router)
    app.include_router(agents_router)
    return app


app = create_app()
