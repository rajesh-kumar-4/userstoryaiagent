from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "author@example.com",
    "GIT_COMMITTER_NAME": "Test Author",
    "GIT_COMMITTER_EMAIL": "author@example.com",
}

# Background gc/maintenance inherits the captured stdout pipe on Windows and
# keeps subprocess.run() blocked after commits. Disable it for test repos.
GIT_NO_BACKGROUND = {
    "GIT_CONFIG_COUNT": "2",
    "GIT_CONFIG_KEY_0": "gc.auto",
    "GIT_CONFIG_VALUE_0": "0",
    "GIT_CONFIG_KEY_1": "maintenance.auto",
    "GIT_CONFIG_VALUE_1": "false",
}


def git(cwd: Path, *args: str) -> str:
    # Output goes to temp files, not pipes: on timeout, a grandchild holding a pipe blocks subprocess.run forever.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            timeout=60,
            env={**os.environ, **GIT_IDENTITY, **GIT_NO_BACKGROUND, "GIT_TERMINAL_PROMPT": "0", "GIT_EDITOR": "true"},
        )
        out.seek(0)
        err.seek(0)
        stdout = out.read().decode("utf-8", errors="replace")
        stderr = err.read().decode("utf-8", errors="replace")
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, ["git", *args], output=stdout, stderr=stderr)
    return stdout.strip()


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def init_repo(path: Path, default_branch: str = "main") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-b", default_branch)
    return path


def commit_all(path: Path, message: str) -> str:
    git(path, "add", "-A")
    git(path, "commit", "-m", message)
    return git(path, "rev-parse", "HEAD")


def remove_tree(path: Path) -> None:
    def make_writable(func, target, _exc_info):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onerror=make_writable)


class FakeClock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now
