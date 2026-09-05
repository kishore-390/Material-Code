from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "One Nation One Common Material Code"

    DATABASE_URL: str = "postgresql+psycopg://material_admin:postgres@postgres:5432/material_harmonization"

    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    JWT_SECRET_KEY: str = "CHANGE_ME_super_secret_key_for_dev_only"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 15

    TEXT_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    IMAGE_EMBEDDING_MODEL: str = "openai/clip-vit-base-patch32"
    EMBEDDING_DIM: int = 384
    IMAGE_EMBEDDING_DIM: int = 512
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

    WEIGHT_DESCRIPTION: float = 0.30
    WEIGHT_SPECIFICATION: float = 0.25
    WEIGHT_CATEGORY: float = 0.15
    WEIGHT_UOM: float = 0.10
    WEIGHT_IMAGE: float = 0.15
    WEIGHT_ATTRIBUTES: float = 0.05

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
