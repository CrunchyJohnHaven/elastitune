import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    app_name: str = "ElastiTune"
    version: str = "0.1.0"
    cost_per_gb_per_month: float = float(os.getenv("COST_PER_GB_MONTH", "0.095"))
    default_persona_count: int = 24
    max_sample_docs: int = 120
    keep_threshold: float = 0.003
    metrics_interval_seconds: float = 2.0
    persona_batch_interval_seconds: float = 1.5
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))


settings = Settings()
