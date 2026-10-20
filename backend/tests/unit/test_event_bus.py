from app.core.events import EventBus
from app.domain.models import ChangeEvent, EventType


def test_publish_delivers_to_typed_and_global_subscribers():
    bus = EventBus()
    typed, global_seen = [], []
    bus.subscribe(typed.append, EventType.FILE_MODIFIED)
    bus.subscribe(global_seen.append)

    delivered = bus.publish(ChangeEvent(type=EventType.FILE_MODIFIED, repository="r"))
    bus.publish(ChangeEvent(type=EventType.COMMIT_CREATED, repository="r"))

    assert delivered == 2
    assert len(typed) == 1
    assert len(global_seen) == 2


def test_duplicate_event_id_is_ignored():
    bus = EventBus()
    event = ChangeEvent(type=EventType.FILE_MODIFIED, repository="r")

    bus.publish(event)
    bus.publish(event)
    assert len(bus.recent()) == 1


def test_failing_handler_is_isolated_and_dead_lettered():
    bus = EventBus()
    received = []

    def broken(event):
        raise RuntimeError("boom")

    bus.subscribe(broken)
    bus.subscribe(received.append)
    bus.publish(ChangeEvent(type=EventType.FILE_MODIFIED, repository="r"))

    assert len(received) == 1
    assert bus.dead_letters()[0].error == "boom"


def test_recent_filters_by_repository_and_type():
    bus = EventBus()
    bus.publish(ChangeEvent(type=EventType.FILE_MODIFIED, repository="a"))
    bus.publish(ChangeEvent(type=EventType.COMMIT_CREATED, repository="b"))

    assert [e.repository for e in bus.recent(repository="a")] == ["a"]
    assert [e.type for e in bus.recent(event_type=EventType.COMMIT_CREATED)] == [EventType.COMMIT_CREATED]
