"""Shared path validation for local-control APIs."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


class PathPolicyError(ValueError):
    """Raised when a requested path is outside the configured local roots."""


def _resolve(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def allowed_roots(defaults: Iterable[Path | str]) -> list[Path]:
    """Return normalized roots that local-control APIs may operate inside."""
    roots: list[Path] = []
    for root in defaults:
        try:
            roots.append(_resolve(root))
        except Exception:
            continue

    extra_roots = os.getenv("APPBUILDER_ALLOWED_ROOTS", "")
    for raw_root in extra_roots.split(os.pathsep):
        raw_root = raw_root.strip()
        if not raw_root:
            continue
        try:
            roots.append(_resolve(raw_root))
        except Exception:
            continue

    if os.getenv("APPBUILDER_ALLOW_TEMP_ROOTS", "").lower() in {"1", "true", "yes"}:
        import tempfile

        try:
            roots.append(_resolve(tempfile.gettempdir()))
        except Exception:
            pass

    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = os.path.normcase(str(root))
        if key not in seen:
            unique.append(root)
            seen.add(key)
    return unique


def ensure_allowed_root(root: Path | str, roots: Iterable[Path | str]) -> Path:
    """Validate that root is under one of the configured allowed roots."""
    candidate = _resolve(root)
    for allowed in roots:
        allowed_path = _resolve(allowed)
        try:
            candidate.relative_to(allowed_path)
            return candidate
        except ValueError:
            continue
    raise PathPolicyError(f"Path is outside allowed roots: {candidate}")


def resolve_safe_path(
    root: Path | str,
    rel_path: Path | str,
    roots: Iterable[Path | str],
) -> tuple[Path, Path]:
    """Resolve rel_path under root after validating both against allowed roots."""
    base = ensure_allowed_root(root, roots)
    target = (base / rel_path).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise PathPolicyError(f"Path escapes root: {rel_path}") from exc
    return base, target
