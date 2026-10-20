"""Agents 1-3: change set, declarations, and dependency manifests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.ast_parser import analyze_source, is_analyzable
from app.agents.base import Agent
from app.agents.code_reader import base_content, current_content
from app.agents.context import SharedContext
from app.agents.dependency_parser import diff_dependencies, manifest_kind, parse_manifest
from app.domain.models import ChangeType
from app.rag.collections import Collection

MAX_FILES = 200
MAX_SYMBOLS = 500
MAX_MANIFESTS = 100
_NO_BASE_TYPES = (ChangeType.ADDED, ChangeType.UNTRACKED)


class GitDiffAgent(Agent):
    index = 1
    name = "git_diff"
    description = "Resolves the change set for the requested scope."
    collection = Collection.CODE_CHANGES

    def run(self, ctx: SharedContext) -> dict[str, Any]:
        change_set = self.deps.change_scope.resolve(ctx.request)
        ctx.change_set = change_set
        return {
            "analysis_mode": change_set.analysis_mode.value,
            "base_sha": change_set.base_sha,
            "target_sha": change_set.target_sha,
            "totals": dict(change_set.totals),
            "files": [change.model_dump(mode="json") for change in change_set.files[:MAX_FILES]],
            "truncated": len(change_set.files) > MAX_FILES,
        }


class AstAnalysisAgent(Agent):
    index = 2
    name = "ast_analysis"
    description = "Extracts declarations from changed source files."
    collection = Collection.AST_ANALYSIS

    def run(self, ctx: SharedContext) -> dict[str, Any]:
        change_set = ctx.require_change_set()
        root = Path(ctx.require_repository().path)
        files: list[dict[str, Any]] = []
        symbols: list[dict[str, Any]] = []
        declaration_total = 0
        parse_errors = 0
        skipped = 0
        for change in change_set.files:
            if change.change_type is ChangeType.DELETED or not is_analyzable(change.path):
                continue
            if len(files) >= MAX_FILES:
                skipped += 1
                continue
            content = current_content(root, change_set, change.path)
            if content is None:
                skipped += 1
                continue
            analysis = analyze_source(change.path, content)
            if analysis is None:
                continue
            if analysis.parse_error:
                parse_errors += 1
            declaration_total += len(analysis.declarations)
            for declaration in analysis.declarations:
                if len(symbols) < MAX_SYMBOLS:
                    symbols.append(
                        {
                            "name": declaration.name,
                            "kind": declaration.kind,
                            "file": change.path,
                            "line": declaration.line,
                            "precision": analysis.precision,
                        }
                    )
            files.append(
                {
                    "path": change.path,
                    "language": analysis.language,
                    "precision": analysis.precision,
                    "declarations": len(analysis.declarations),
                    "imports": analysis.imports,
                    "parse_error": analysis.parse_error,
                }
            )
        return {
            "files": files,
            "declaration_count": declaration_total,
            "symbols": symbols,
            "parse_errors": parse_errors,
            "skipped_files": skipped,
        }


class DependencyAnalysisAgent(Agent):
    index = 3
    name = "dependency_analysis"
    description = "Diffs dependency manifests between the base and target of the change set."
    collection = Collection.DEPENDENCY_ANALYSIS

    def run(self, ctx: SharedContext) -> dict[str, Any]:
        change_set = ctx.require_change_set()
        root = Path(ctx.require_repository().path)
        manifests: list[dict[str, Any]] = []
        added_total = removed_total = changed_total = 0
        for change in change_set.files:
            kind = manifest_kind(Path(change.path).name)
            if kind is None:
                continue
            base_text = (
                None
                if change.change_type in _NO_BASE_TYPES
                else base_content(root, change_set, change.old_path or change.path)
            )
            current_text = None if change.change_type is ChangeType.DELETED else current_content(root, change_set, change.path)
            entry: dict[str, Any] = {"path": change.path, "kind": kind, "parse_error": None}
            try:
                base = parse_manifest(kind, base_text) if base_text else {}
                current = parse_manifest(kind, current_text) if current_text else {}
            except ValueError as exc:
                entry.update({"added": [], "removed": [], "changed": []})
                entry["parse_error"] = str(exc)[:200]
                manifests.append(entry)
                continue
            diff = diff_dependencies(base, current)
            entry.update(diff)
            added_total += len(diff["added"])
            removed_total += len(diff["removed"])
            changed_total += len(diff["changed"])
            manifests.append(entry)
        return {
            "manifests": manifests[:MAX_MANIFESTS],
            "manifest_count": len(manifests),
            "added": added_total,
            "removed": removed_total,
            "changed": changed_total,
        }
