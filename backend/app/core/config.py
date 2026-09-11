from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "One Nation - One Common Material Code"

    DATABASE_URL: str = "postgresql+psycopg://material_admin:postgres@postgres:5432/material_harmonization"

    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    JWT_SECRET_KEY: str = "CHANGE_ME_super_secret_key_for_dev_only"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    TEXT_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    AI_USE_MOCK_FALLBACK: bool = True

    # Optional trained XGBoost material-match classifier. Absent by default -
    # see app/ml/train_xgb_ranker.py for how one would be produced from a
    # labeled dataset. Until a file exists at this path, the ML score is
    # reported as unavailable and the existing weighted rule-based score
    # remains the sole basis for the harmonization decision.
    XGB_MODEL_PATH: str = "app/ml_models/material_match_xgb.json"

    THRESHOLD_AUTO: float = 95.0
    THRESHOLD_REVIEW: float = 85.0
    THRESHOLD_LOW: float = 60.0

    # Component weights (spec section 7.5) - must sum to 1.0. "manufacturer"
    # only applies when at least one side is flagged criticality=CRITICAL
    # (spec section 6 point 7); otherwise its weight is redistributed - see
    # app.services.scoring.compute_final_score.
    WEIGHT_DESCRIPTION: float = 0.20
    WEIGHT_SPECIFICATION: float = 0.15
    WEIGHT_CLASSIFICATION: float = 0.10
    WEIGHT_UOM: float = 0.05
    WEIGHT_ATTRIBUTES: float = 0.05
    WEIGHT_GRADE: float = 0.15
    WEIGHT_DIMENSION: float = 0.15
    WEIGHT_STANDARD: float = 0.05
    WEIGHT_MANUFACTURER: float = 0.03
    WEIGHT_FUNCTION: float = 0.05
    WEIGHT_CRITICALITY: float = 0.02

    # Source connector defaults (spec section 26-27) - per-connection
    # overrides live on source_connections, never here.
    SOURCE_SYNC_DEFAULT_PAGE_SIZE: int = 500
    SOURCE_SYNC_BEAT_TICK_SECONDS: int = 30
    SOURCE_SYNC_MAX_PAGES_PER_RUN: int = 500
    # Only used when a caller opts into wait_for_settlement=True (e.g.
    # app.demo_seed) - how long to block for that batch's automatic
    # post-sync harmonization pass to finish (see app.connectors.sync_engine).
    SOURCE_SYNC_SETTLE_TIMEOUT_SECONDS: int = 120

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
