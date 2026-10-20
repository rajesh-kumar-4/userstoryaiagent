from dependency_injector import containers, providers

from app.agents.audit import AuditLogger
from app.agents.base import AgentDeps
from app.agents.context import ContextManager
from app.agents.workflow import AgentWorkflowManager
from app.config import Settings
from app.core.events import EventBus
from app.core.llm.prompt_manager import PromptManager
from app.core.llm.provider_factory import create_llm_provider
from app.core.security.rbac import Authenticator
from app.integrations.security.factory import build_security_scanners
from app.mcp.registry import ToolRegistry
from app.rag.ingest import build_ingestor
from app.rag.retrieval import Retriever
from app.rag.store import build_vector_store
from app.services.analysis_service import AnalysisService
from app.services.analysis_store import AnalysisStore
from app.services.branch_comparison import BranchComparisonService
from app.services.branch_discovery import BranchDiscoveryService
from app.services.change_detection import ChangeDetectionEngine
from app.services.change_scope import ChangeScopeResolver
from app.services.commit_discovery import CommitDiscoveryService
from app.services.dashboard_service import DashboardService
from app.services.git_metadata import GitMetadataService
from app.services.pull_request_service import LocalRefPullRequestProvider, PullRequestService
from app.services.repository_discovery import RepositoryDiscoveryEngine
from app.services.repository_explorer import RepositoryExplorer
from app.services.repository_registry import RepositoryRegistry
from app.services.rule_analyzer import RuleBasedAnalyzer
from app.services.security_scan_service import SecurityScanService
from app.services.workspace_analysis import WorkspaceAnalysisService
from app.services.workspace_monitor import MonitorConfig, WorkspaceMonitor
from app.services.workspace_scanner import WorkspaceScanner


class AppContainer(containers.DeclarativeContainer):
    settings = providers.Dependency(instance_of=Settings)

    event_bus = providers.Singleton(EventBus, history_size=settings.provided.event_history_size)
    scanner = providers.Singleton(
        WorkspaceScanner,
        root=settings.provided.workspace_root,
        max_depth=settings.provided.max_discovery_depth,
        ignored_directories=settings.provided.ignored_directories,
        platform_root=settings.provided.platform_root,
    )
    discovery = providers.Singleton(RepositoryDiscoveryEngine, scanner=scanner)
    registry = providers.Singleton(RepositoryRegistry, discovery=discovery, bus=event_bus)

    branch_discovery = providers.Singleton(BranchDiscoveryService)
    commit_discovery = providers.Singleton(CommitDiscoveryService)
    metadata = providers.Singleton(GitMetadataService)
    comparison = providers.Singleton(BranchComparisonService)
    pull_request_provider = providers.Singleton(LocalRefPullRequestProvider)
    pull_requests = providers.Singleton(
        PullRequestService, provider=pull_request_provider, comparison=comparison
    )
    change_scope = providers.Singleton(
        ChangeScopeResolver,
        registry=registry,
        commits=commit_discovery,
        comparison=comparison,
        pulls=pull_requests,
    )
    explorer = providers.Singleton(
        RepositoryExplorer,
        registry=registry,
        branches=branch_discovery,
        commits=commit_discovery,
        metadata=metadata,
        scope=change_scope,
        pulls=pull_requests,
    )
    workspace_analysis = providers.Singleton(WorkspaceAnalysisService, registry=registry)

    authenticator = providers.Singleton(
        Authenticator,
        enabled=settings.provided.auth_enabled,
        api_keys=settings.provided.api_keys,
    )
    llm_provider = providers.Singleton(create_llm_provider, settings=settings)
    prompt_manager = providers.Singleton(PromptManager)
    security_scanners = providers.Singleton(build_security_scanners, settings=settings)
    security_scans = providers.Singleton(
        SecurityScanService,
        scanners=security_scanners,
        project_keys=settings.provided.security_project_keys,
    )
    analysis_store = providers.Singleton(AnalysisStore, max_entries=settings.provided.analysis_history_size)
    rule_analyzer = providers.Singleton(RuleBasedAnalyzer)
    analysis = providers.Singleton(
        AnalysisService,
        registry=registry,
        change_scope=change_scope,
        analyzer=rule_analyzer,
        store=analysis_store,
        security=security_scans,
        history=workspace_analysis,
        bus=event_bus,
        prompts=prompt_manager,
        llm=llm_provider,
    )
    dashboard = providers.Singleton(DashboardService, registry=registry, store=analysis_store)

    detection = providers.Singleton(ChangeDetectionEngine, watch_patterns=settings.provided.watch_patterns)
    monitor_config = providers.Singleton(
        MonitorConfig,
        mode=settings.provided.monitor_mode,
        interval_seconds=settings.provided.monitor_interval_seconds,
        debounce_seconds=settings.provided.monitor_debounce_seconds,
    )
    monitor = providers.Singleton(
        WorkspaceMonitor,
        registry=registry,
        detection=detection,
        bus=event_bus,
        config=monitor_config,
    )

    tool_registry = providers.Singleton(ToolRegistry)

    vector_store = providers.Singleton(
        build_vector_store,
        chroma_path=settings.provided.chroma_path,
        chroma_host=settings.provided.chroma_host,
        chroma_port=settings.provided.chroma_port,
    )
    retriever = providers.Singleton(Retriever, store=vector_store)
    rag_ingestor = providers.Singleton(build_ingestor, settings=settings, store=vector_store)
    context_manager = providers.Singleton(ContextManager, history_size=settings.provided.agent_run_history_size)
    audit_logger = providers.Singleton(AuditLogger)
    agent_deps = providers.Singleton(
        AgentDeps,
        settings=settings,
        registry=registry,
        explorer=explorer,
        change_scope=change_scope,
        analyzer=rule_analyzer,
        security=security_scans,
        history=workspace_analysis,
        retriever=retriever,
        prompts=prompt_manager,
        llm=llm_provider,
    )
    agent_workflow = providers.Singleton(
        AgentWorkflowManager,
        tools=tool_registry,
        deps=agent_deps,
        contexts=context_manager,
        audit=audit_logger,
        store=vector_store,
        bus=event_bus,
    )


def build_container(settings: Settings) -> AppContainer:
    container = AppContainer()
    container.settings.override(providers.Object(settings))
    return container
