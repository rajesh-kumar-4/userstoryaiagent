"""Dependency manifest parsers. Each returns a mapping of dependency name to version specifier."""

from __future__ import annotations

import json
import re
from collections.abc import Callable

_POM_DEPENDENCY = re.compile(
    r"<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>(?:\s*<version>([^<]+)</version>)?",
    re.DOTALL,
)
_GRADLE_DEPENDENCY = re.compile(
    r"""^\s*(?:implementation|api|compileOnly|runtimeOnly|testImplementation|testRuntimeOnly|"""
    r"""annotationProcessor|compile|testCompile)\s*\(?\s*["']([^"':\s]+):([^"':\s]+)(?::([^"':\s]+))?["']""",
    re.MULTILINE,
)
_GO_REQUIRE = re.compile(
    r"^\s*(?:require\s+)?([A-Za-z0-9][\w.\-]*(?:/[\w.\-]+)+)\s+(v[\w.\-+]+)(?:\s+//.*)?\s*$",
    re.MULTILINE,
)
_PIP_REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*(.*?)\s*(?:;.*)?$")
_NPM_SECTIONS = ("dependencies", "devDependencies", "peerDependencies")
UNPINNED = "*"


def manifest_kind(filename: str) -> str | None:
    lower = filename.lower()
    if lower == "package.json":
        return "npm"
    if lower == "pom.xml":
        return "maven"
    if lower in ("build.gradle", "build.gradle.kts"):
        return "gradle"
    if lower == "go.mod":
        return "go"
    if lower.startswith("requirements") and lower.endswith(".txt"):
        return "pip"
    return None


def _parse_npm(content: str) -> dict[str, str]:
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("package.json must contain a JSON object")
    deps: dict[str, str] = {}
    for section in _NPM_SECTIONS:
        block = data.get(section) or {}
        if isinstance(block, dict):
            deps.update({str(name): str(spec) for name, spec in block.items()})
    return deps


def _parse_maven(content: str) -> dict[str, str]:
    return {
        f"{group}:{artifact}": (version or UNPINNED).strip()
        for group, artifact, version in _POM_DEPENDENCY.findall(content)
    }


def _parse_gradle(content: str) -> dict[str, str]:
    return {
        f"{group}:{artifact}": version or UNPINNED
        for group, artifact, version in _GRADLE_DEPENDENCY.findall(content)
    }


def _parse_go(content: str) -> dict[str, str]:
    return {module: version for module, version in _GO_REQUIRE.findall(content)}


def _parse_pip(content: str) -> dict[str, str]:
    deps: dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.split(" #", 1)[0].strip()
        if not line or line.startswith(("#", "-")):
            continue
        match = _PIP_REQUIREMENT.match(line)
        if match is None:
            continue
        name = re.sub(r"[-_.]+", "-", match.group(1)).lower()
        deps[name] = match.group(2).strip() or UNPINNED
    return deps


_PARSERS: dict[str, Callable[[str], dict[str, str]]] = {
    "npm": _parse_npm,
    "maven": _parse_maven,
    "gradle": _parse_gradle,
    "go": _parse_go,
    "pip": _parse_pip,
}


def parse_manifest(kind: str, content: str) -> dict[str, str]:
    parser = _PARSERS.get(kind)
    if parser is None:
        raise ValueError(f"unsupported manifest kind: {kind}")
    return parser(content)


def diff_dependencies(base: dict[str, str], current: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    added = [{"name": name, "version": current[name]} for name in sorted(current.keys() - base.keys())]
    removed = [{"name": name, "version": base[name]} for name in sorted(base.keys() - current.keys())]
    changed = [
        {"name": name, "from": base[name], "to": current[name]}
        for name in sorted(base.keys() & current.keys())
        if base[name] != current[name]
    ]
    return {"added": added, "removed": removed, "changed": changed}
