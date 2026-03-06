from __future__ import annotations

import os
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def project_root() -> Path:
    return _PROJECT_ROOT


def resolve_runtime_path(path: str | Path, base_dir: str | Path | None = None) -> Path:
    candidate = Path(str(path))
    if not candidate.is_absolute():
        root = Path(base_dir) if base_dir is not None else Path.cwd()
        candidate = root / candidate
    return candidate.resolve()


def portable_path(path: str | Path, base_dir: str | Path | None = None) -> str:
    raw = str(path or "").strip()
    if not raw:
        return ""

    resolved = resolve_runtime_path(raw, base_dir=base_dir)
    roots: list[Path] = []
    if base_dir is not None:
        try:
            roots.append(Path(base_dir).resolve())
        except Exception:
            pass
    roots.append(project_root())

    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        try:
            return str(resolved.relative_to(root))
        except ValueError:
            pass
        try:
            return os.path.relpath(str(resolved), str(root))
        except ValueError:
            pass

    return resolved.name or str(resolved)
