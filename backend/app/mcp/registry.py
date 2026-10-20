from __future__ import annotations

import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

ToolHandler = Callable[[dict[str, Any]], Any]

_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "object": (dict,),
    "array": (list,),
}


class ToolError(Exception):
    pass


class ToolNotFoundError(ToolError):
    pass


class ToolArgumentError(ToolError):
    pass


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler


def _validate_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> None:
    properties = schema.get("properties", {})
    for key in schema.get("required", []):
        if arguments.get(key) is None:
            raise ToolArgumentError(f"Missing required argument: {key}")
    for key, value in arguments.items():
        expected = properties.get(key, {}).get("type")
        if value is None or expected is None:
            continue
        valid = isinstance(value, _JSON_TYPES.get(expected, (object,)))
        if expected in ("integer", "number") and isinstance(value, bool):
            valid = False
        if not valid:
            raise ToolArgumentError(f"Argument '{key}' must be of type {expected}")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._lock = threading.RLock()

    def register(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: ToolHandler,
    ) -> None:
        if not _NAME_PATTERN.match(name):
            raise ValueError(f"Invalid tool name: {name}")
        with self._lock:
            if name in self._tools:
                raise ValueError(f"Tool already registered: {name}")
            self._tools[name] = ToolDefinition(name, description, input_schema, handler)

    def unregister(self, name: str) -> None:
        with self._lock:
            self._tools.pop(name, None)

    def list_tools(self) -> list[dict[str, Any]]:
        with self._lock:
            tools = sorted(self._tools.values(), key=lambda tool: tool.name)
        return [{"name": tool.name, "description": tool.description, "inputSchema": tool.input_schema} for tool in tools]

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        with self._lock:
            tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError(f"Unknown tool: {name}")
        _validate_arguments(tool.input_schema, arguments)
        return tool.handler(arguments)
