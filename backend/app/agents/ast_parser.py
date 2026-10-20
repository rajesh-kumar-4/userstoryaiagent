"""Declaration extraction for changed source files.

Python is parsed with the standard `ast` module (precision "exact"). Other languages use declaration
patterns (precision "pattern", approximate). Only top-level declarations and class methods are reported.
"""

from __future__ import annotations

import ast
import re
from bisect import bisect_left
from dataclasses import dataclass, field
from pathlib import PurePosixPath

PYTHON_SUFFIX = ".py"
PATTERN_LANGUAGES: dict[str, str] = {
    ".java": "java",
    ".kt": "kotlin",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".cs": "csharp",
    ".rb": "ruby",
    ".rs": "rust",
    ".scala": "scala",
}
ANALYZABLE_SUFFIXES = frozenset({PYTHON_SUFFIX, *PATTERN_LANGUAGES})
MAX_DECLARATIONS_PER_FILE = 500

_TYPE_DECLARATION = re.compile(
    r"^\s*(?:(?:export|public|private|protected|internal|static|abstract|final|sealed|open|data|default|declare)\s+)*"
    r"(?:class|interface|enum|record|struct|trait|object)\s+([A-Za-z_]\w*)",
    re.MULTILINE,
)
_FUNCTION_DECLARATION = re.compile(
    r"^\s*(?:(?:export|public|private|protected|internal|static|async|default|suspend|override)\s+)*"
    r"(?:function\s+|fun\s+|func\s+(?:\([^)]*\)\s*)?)([A-Za-z_]\w*)",
    re.MULTILINE,
)
_IMPORT_LINE = re.compile(r"^\s*(?:import|using)\b", re.MULTILINE)


@dataclass(frozen=True)
class Declaration:
    name: str
    kind: str
    line: int


@dataclass
class SourceAnalysis:
    language: str
    precision: str
    declarations: list[Declaration] = field(default_factory=list)
    imports: int = 0
    parse_error: str | None = None


def is_analyzable(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in ANALYZABLE_SUFFIXES


def analyze_source(path: str, content: str) -> SourceAnalysis | None:
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == PYTHON_SUFFIX:
        return _analyze_python(content)
    language = PATTERN_LANGUAGES.get(suffix)
    if language is None:
        return None
    return _analyze_pattern(language, content)


def _analyze_python(content: str) -> SourceAnalysis:
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError) as exc:
        line = getattr(exc, "lineno", None)
        message = f"syntax error at line {line}" if line else "unparseable source"
        return SourceAnalysis(language="python", precision="exact", parse_error=message)

    declarations: list[Declaration] = []
    imports = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            declarations.append(Declaration(node.name, "function", node.lineno))
        elif isinstance(node, ast.ClassDef):
            declarations.append(Declaration(node.name, "class", node.lineno))
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    declarations.append(Declaration(member.name, "method", member.lineno))
    return SourceAnalysis(
        language="python",
        precision="exact",
        declarations=declarations[:MAX_DECLARATIONS_PER_FILE],
        imports=imports,
    )


def _analyze_pattern(language: str, content: str) -> SourceAnalysis:
    newline_offsets = [match.start() for match in re.finditer("\n", content)]
    declarations: list[Declaration] = []
    for pattern, kind in ((_TYPE_DECLARATION, "type"), (_FUNCTION_DECLARATION, "function")):
        for match in pattern.finditer(content):
            line = bisect_left(newline_offsets, match.start(1)) + 1
            declarations.append(Declaration(match.group(1), kind, line))
    declarations.sort(key=lambda declaration: declaration.line)
    return SourceAnalysis(
        language=language,
        precision="pattern",
        declarations=declarations[:MAX_DECLARATIONS_PER_FILE],
        imports=len(_IMPORT_LINE.findall(content)),
    )
