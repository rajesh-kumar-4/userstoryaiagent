from pathlib import Path

from app.domain.models import EventType, MonitorMode
from app.services.change_detection import ChangeDetectionEngine
from app.services.workspace_monitor import MonitorConfig, WorkspaceMonitor
from tests.support import FakeClock, commit_all, write


def test_commit_is_detected_on_second_cycle(container, sample_workspace: Path):
    monitor = container.monitor()
    assert monitor.run_cycle() == []

    repo = sample_workspace / "billing-service"
    write(repo / "src" / "main" / "Service.java", "class Service {}\n")
    commit_all(repo, "add service")

    events = [event for event in monitor.run_cycle() if event.repository == "billing-service"]
    types = {event.type for event in events}

    assert EventType.COMMIT_CREATED in types
    assert EventType.FILE_MODIFIED in types
    assert monitor.status().tracked_repositories == 3


def test_debounce_holds_events_until_window_elapses(container, settings, sample_workspace: Path):
    clock = FakeClock(0.0)
    monitor = WorkspaceMonitor(
        container.registry(),
        ChangeDetectionEngine(settings.watch_patterns),
        container.event_bus(),
        MonitorConfig(mode=MonitorMode.MANUAL, interval_seconds=30, debounce_seconds=10),
        clock=clock,
    )
    monitor.run_cycle()

    repo = sample_workspace / "frontend" / "web-app"
    write(repo / "src" / "index.js", "console.log('changed');\n")
    clock.now = 1.0
    assert monitor.run_cycle() == []
    assert monitor.status().pending_events > 0

    clock.now = 12.0
    flushed = monitor.run_cycle()

    assert flushed
    assert monitor.status().pending_events == 0

