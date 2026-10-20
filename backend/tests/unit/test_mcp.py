import json

from app.mcp.registry import ToolRegistry
from app.mcp.server import handle_message


def _registry() -> ToolRegistry:
    tools = ToolRegistry()
    tools.register(
        "echo",
        "Echo the text argument.",
        {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        lambda args: {"text": args["text"]},
    )
    tools.register("explode", "Always fails.", {"type": "object", "properties": {}}, _fail)
    return tools


def _fail(args):
    raise ValueError("bad input")


def test_initialize_reports_protocol_and_tool_capability():
    response = handle_message(_registry(), {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})

    assert response["result"]["protocolVersion"]
    assert "tools" in response["result"]["capabilities"]


def test_tools_list_returns_registered_tools_sorted():
    response = handle_message(_registry(), {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    assert [tool["name"] for tool in response["result"]["tools"]] == ["echo", "explode"]


def test_tools_call_returns_json_text_content():
    response = handle_message(
        _registry(),
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "echo", "arguments": {"text": "hi"}}},
    )

    assert response["result"]["isError"] is False
    assert json.loads(response["result"]["content"][0]["text"]) == {"text": "hi"}


def test_tool_failure_is_reported_as_error_result():
    response = handle_message(
        _registry(),
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "explode", "arguments": {}}},
    )

    assert response["result"]["isError"] is True
    assert "bad input" in response["result"]["content"][0]["text"]


def test_missing_or_mistyped_arguments_are_invalid_params():
    missing = handle_message(
        _registry(),
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "echo", "arguments": {}}},
    )
    mistyped = handle_message(
        _registry(),
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "echo", "arguments": {"text": 3}}},
    )

    assert missing["error"]["code"] == -32602
    assert mistyped["error"]["code"] == -32602


def test_unknown_method_and_invalid_envelope_are_rejected():
    unknown = handle_message(_registry(), {"jsonrpc": "2.0", "id": 7, "method": "resources/list"})
    invalid = handle_message(_registry(), {"id": 8})

    assert unknown["error"]["code"] == -32601
    assert invalid["error"]["code"] == -32600


def test_notifications_receive_no_response():
    assert handle_message(_registry(), {"jsonrpc": "2.0", "method": "ping"}) is None
