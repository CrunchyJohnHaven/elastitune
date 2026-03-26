from __future__ import annotations

from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "ElastiTune"
    version: str = "0.1.0"
    cost_per_gb_per_month: float = 0.095
    default_persona_count: int = 24
    max_sample_docs: int = 120
    keep_threshold: float = 0.001
    metrics_interval_seconds: float = 2.0
    persona_batch_interval_seconds: float = 1.5
    use_split_managers: bool = True
    committee_persistence_enabled: bool = True
    use_msearch_eval: bool = False
    emit_invariant_events: bool = True
    enable_elastic_sink: bool = False
    elastic_sink_url: str | None = None
    elastic_sink_api_key: str | None = None
    elastic_sink_search_runs_prefix: str = "elastitune-search-runs"
    elastic_sink_search_experiments_prefix: str = "elastitune-search-experiments"
    elastic_sink_committee_runs_prefix: str = "elastitune-committee-runs"
    max_committee_upload_bytes: int = 8 * 1024 * 1024
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> List[str]:
        if value is None:
            return ["*"]
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, (list, tuple)):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        return ["*"]


settings = Settings()
