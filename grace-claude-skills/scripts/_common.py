"""Shared bootstrap for the grace-claude-skills helper scripts.

These scripts import GrACE's own models so the rows/payloads they write are
schema-correct. We chdir into the repo root so that pydantic-settings (.env)
and the relative config/discovery.yaml load resolve, add the repo root to
sys.path so `import src.*` works, and export `.env` into the process
environment so provider switches such as GRACE_EMBED_PROVIDER are honoured
even when the operator never `source`d the file.

Root resolution: `--grace-root` arg → `GRACE_ROOT` env → the checkout that
contains this file (the normal case for a cloned GrACE-Demo).

No LLM calls happen here. DB / HTTP reads and writes only.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Default to THIS checkout — the repo containing this file — never a guessed
# home-relative path. Explicit arg / GRACE_ROOT still override.
DEFAULT_GRACE_ROOT = str(Path(__file__).resolve().parents[2])


def route_logs_to_stderr(quiet: bool = False) -> None:
    """Send grace's structlog output to stderr so CLI helpers can emit clean JSON
    on stdout. Grace configures structlog with a stdout PrintLogger on import; its
    ``arcade.query`` info lines otherwise interleave with a helper's JSON payload and
    break downstream `json.load`. Call AFTER grace modules are imported (last
    `structlog.configure` wins). Best-effort — never fatal.

    R6 (session-4): ``quiet=True`` additionally raises the log floor to WARNING (so the
    ~20-40 per-call ``arcade.query`` INFO lines stop entirely — the unanimous cold-start
    friction) and silences Pydantic ``UserWarning`` noise. This is the default for the
    probe CLIs; pass ``--verbose`` to restore full INFO logs.
    """
    try:
        import structlog  # noqa: E402

        cfg = structlog.get_config()
        kwargs = dict(
            processors=cfg.get("processors"),
            logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        )
        if quiet:
            import logging
            import warnings

            warnings.filterwarnings("ignore", category=UserWarning)
            kwargs["wrapper_class"] = structlog.make_filtering_bound_logger(logging.WARNING)
            logging.getLogger().setLevel(logging.WARNING)
        structlog.configure(**kwargs)
    except Exception:  # pragma: no cover - logging is non-critical
        pass


def add_grace_to_path(grace_root: str | None = None) -> Path:
    """Resolve the repo root, chdir into it, and put it on sys.path.

    chdir matters: GraceSettings reads `.env` and config loaders read
    `config/discovery.yaml` via paths relative to the current working directory.
    """
    root = Path(grace_root or os.environ.get("GRACE_ROOT") or DEFAULT_GRACE_ROOT).expanduser().resolve()
    if not (root / "src").is_dir():
        raise SystemExit(f"[grace-claude-skills] grace root not found at {root} (no src/).")
    # Always announce which checkout we execute against.
    print(f"[grace-claude-skills] grace root: {root}", file=sys.stderr)
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    _export_dotenv(root / ".env")
    return root


def _export_dotenv(env_path: Path) -> None:
    """Load `.env` into os.environ (existing exported vars win).

    pydantic-settings reads `.env` for GraceSettings, but plain `os.environ`
    readers (src.shared.embeddings → GRACE_EMBED_*) do not. Without this a
    student who set GRACE_EMBED_PROVIDER in `.env` would still hit the legacy
    Ollama inference path from these helpers. Best-effort, never fatal.
    """
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv  # bundled with pydantic-settings

        load_dotenv(env_path, override=False)
        return
    except Exception:  # noqa: BLE001 — fall back to a minimal parser
        pass
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:  # noqa: BLE001
        pass


def get_session(grace_root: str | None = None):
    """Return a live SQLAlchemy session bound to the configured GrACE DB.

    The target comes from `DATABASE_URL` in `.env` (GrACE-Demo: `grace_demo`).
    These helpers populate the live onboarding pipeline; only pytest runs against
    an isolated `_test` sibling (see safe_pytest.sh).
    """
    add_grace_to_path(grace_root)
    from src.shared.database import get_session_factory  # noqa: E402

    return get_session_factory()()


def distinct_domains(db) -> list[str]:
    """Distinct domains that have at least one COMPLETE processed document."""
    from src.discovery.database import ProcessedDocumentRow  # noqa: E402

    rows = (
        db.query(ProcessedDocumentRow.domain)
        .filter(ProcessedDocumentRow.status == "COMPLETE")
        .distinct()
        .all()
    )
    return sorted({r[0] for r in rows if r[0]})
