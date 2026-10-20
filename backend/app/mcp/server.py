from __future__ import annotations

import json
from typing import Any

from pydantic_core import to_jsonable_python

from app.mcp.registry import ToolArgumentError, ToolError, ToolNotFoundError, ToolRegistry

PROTOCOL_VERSION = "2025-03-26"
SERVER_INFO = {"name": "userstoryai-repository-intelligence", "version": "0.2.0"}

INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _tool_result(payload: Any, is_error: bool) -> dict[str, Any]:
    text = payload if is_error else json.dumps(to_jsonable_python(payload))
    return {"content": [{"type": "text", "text": str(text)}], "isError": is_error}


def handle_message(tools: ToolRegistry, message: Any) -> dict[str, Any] | None:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return _error(None, INVALID_REQUEST, "Invalid JSON-RPC request")

    if "id" not in message:
        return None

    request_id = message["id"]
    method = message["method"]
    params = message.get("params") or {}

    if method == "initialize":
        result: dict[str, Any] = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": True}},
            "serverInfo": SERVER_INFO,
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": tools.list_tools()}
    elif method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return _error(request_id, INVALID_PARAMS, "tools/call requires a name and object arguments")
        try:
            result = _tool_result(tools.call(name, arguments), is_error=False)
        except (ToolNotFoundError, ToolArgumentError) as exc:
            return _error(request_id, INVALID_PARAMS, str(exc))
        except ToolError as exc:
            result = _tool_result(str(exc), is_error=True)
        except Exception as exc:
            result = _tool_result(f"{type(exc).__name__}: {exc}", is_error=True)
    else:
        return _error(request_id, METHOD_NOT_FOUND, f"Method not found: {method}")

    return {"jsonrpc": "2.0", "id": request_id, "result": result}
