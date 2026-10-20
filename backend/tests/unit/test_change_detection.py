from app.domain.models import EventType
from app.services.change_detection import RepositorySnapshot, classify_file, diff_snapshots
from app.domain.models import FileStamp


def _snapshot(**overrides) -> RepositorySnapshot:
    base = {
        "repository": "billing-service",
        "current_branch": "main",
        "head_sha": "a" * 40,
        "branch_heads": {"main": "a" * 40},
        "pr_refs": {},
        "files": {},
    }
    base.update(overrides)
    return RepositorySnapshot(**base)


def test_classify_file_maps_manifests_and_configs():
    assert classify_file("pom.xml") is EventType.DEPENDENCY_UPDATED
    assert classify_file("services/api/requirements-dev.txt") is EventType.DEPENDENCY_UPDATED
    assert classify_file("src/main/resources/application-prod.yml") is EventType.CONFIG_UPDATED
    assert classify_file("src/main/App.java") is EventType.FILE_MODIFIED


def test_first_snapshot_produces_no_events():
    assert diff_snapshots(None, _snapshot()) == []


def test_new_commit_on_branch_is_reported():
    previous = _snapshot()
    current = _snapshot(branch_heads={"main": "b" * 40}, head_sha="b" * 40)

    events = diff_snapshots(previous, current)

    assert [event.type for event in events] == [EventType.COMMIT_CREATED]
    assert events[0].branch == "main"


def test_merge_commit_is_reported_as_merge():
    previous = _snapshot()
    current = _snapshot(branch_heads={"main": "b" * 40})

    events = diff_snapshots(previous, current, merge_commits=frozenset({"b" * 40}))

    assert events[0].type is EventType.MERGE_COMPLETED


def test_branch_switch_and_new_pull_request_ref_are_reported():
    previous = _snapshot()
    current = _snapshot(current_branch="feature/PAY-1", pr_refs={"refs/pull/7/head": "c" * 40})

    types = {event.type for event in diff_snapshots(previous, current)}

    assert EventType.BRANCH_CHANGED in types
    assert EventType.PR_CREATED in types


def test_file_stamp_changes_and_deletions_are_reported():
    previous = _snapshot(files={"src/A.java": FileStamp(10, 1), "pom.xml": FileStamp(5, 1)})
    current = _snapshot(files={"src/A.java": FileStamp(12, 2)})

    events = diff_snapshots(previous, current)
    by_file = {event.file: event.type for event in events if event.file}

    assert by_file["src/A.java"] is EventType.FILE_MODIFIED
    assert by_file["pom.xml"] is EventType.FILE_DELETED
