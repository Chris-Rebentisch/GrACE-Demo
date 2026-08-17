"""GrACE-wide configuration loaded from .env at project root."""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _export_dotenv_to_environ() -> None:
    """Export `.env` (project root, then CWD) into ``os.environ`` without
    overriding variables that are already set.

    pydantic-settings reads `.env` for :class:`GraceSettings`, but several
    plain ``os.environ`` readers (``GRACE_EMBED_*`` in ``src.shared.embeddings``,
    ``GRACE_ADMIN_KEY`` in the auth middleware, ``GRACE_PERMISSION_ENFORCEMENT_ENABLED``)
    would otherwise only work when the operator ``export``ed the file by hand.
    GrACE-Demo students never do that, so make `.env` authoritative here.
    Best-effort: never raises.
    """
    if os.environ.get("GRACE_PYTEST_MODE") == "1":
        # Under pytest the suite must be hermetic: tests/conftest.py decides the
        # environment; the operator's `.env` is read only via GraceSettings.
        return
    candidates = [Path(__file__).resolve().parents[2] / ".env", Path.cwd() / ".env"]
    for env_path in candidates:
        if not env_path.is_file():
            continue
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path, override=False)
        except Exception:  # noqa: BLE001 — minimal fallback parser
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
        return


_export_dotenv_to_environ()


class GraceSettings(BaseSettings):
    """GrACE-wide configuration. Loaded from .env at project root."""

    # PostgreSQL
    database_url: str = Field(description="SQLAlchemy connection string for PostgreSQL")

    # Ollama
    ollama_base_url: str = Field(
        default="http://localhost:11434", description="Ollama API base URL"
    )
    ollama_model: str = Field(
        default="qwen2.5:7b", description="Primary Ollama model for inference"
    )
    ollama_embed_model: str = Field(
        default="nomic-embed-text", description="Ollama embedding model"
    )
    ollama_timeout: int = Field(
        default=300, description="Ollama request timeout in seconds"
    )

    # LLM API Key (for cloud providers)
    llm_api_key: str = Field(
        default="", description="API key for cloud LLM providers (Anthropic, OpenAI, etc.)"
    )

    # FastAPI
    grace_host: str = Field(default="localhost", description="FastAPI bind host")
    grace_port: int = Field(default=8000, description="FastAPI bind port")

    # ArcadeDB
    arcade_host: str = Field(default="localhost", description="ArcadeDB server host")
    arcade_port: int = Field(default=2480, description="ArcadeDB HTTP API port")
    arcade_username: str = Field(default="root", description="ArcadeDB username")
    arcade_password: str = Field(
        default="gracedev", description="ArcadeDB root password"
    )
    arcade_database: str = Field(
        default="grace", description="ArcadeDB database name"
    )
    arcade_timeout: int = Field(
        default=30, description="ArcadeDB request timeout in seconds"
    )

    # Retrieval
    embedding_dim: int = Field(
        default=768, description="Embedding dimension (auto-detected from Ollama)"
    )
    retrieval_rrf_k: int = Field(default=60, description="RRF damping constant")
    retrieval_reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Cross-encoder model for reranking",
    )
    retrieval_top_k: int = Field(default=10, description="Final result count")
    retrieval_serialization_format: str = Field(
        default="template", description="template|turtle|llm"
    )
    retrieval_temporal_as_strategy: bool = Field(
        default=False,
        description="True=temporal as separate RRF strategy, False=filter on graph results",
    )

    # Discovery
    discovery_source_dir: str = Field(
        default="data/discovery-sample",
        description="Default directory for Discovery document input",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> GraceSettings:
    """Return a cached singleton GraceSettings instance."""
    return GraceSettings()
