from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    MODEL_PATH: str = "../models/fashionpedia_9class_with_data_augmentation.pt"
    CONF_THRES: float = 0.25
    OPENAI_MODEL: str = "gpt-5.4-nano"
    OPENAI_MAX_RETRIES: int = 2
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_CHUNK_SIZE_BYTES: int = 1048576
    MAX_IMAGE_WIDTH: int = 8000
    MAX_IMAGE_HEIGHT: int = 8000
    MAX_IMAGE_PIXELS: int = 40000000
    MAX_IMAGE_LONG_SIDE: int = 1280
    SQLITE_BUSY_TIMEOUT_MS: int = 5000
    PROCESSING_STALE_MINUTES: int = 10
    AI_MAX_CONCURRENCY: int = 1
    MIN_FREE_STORAGE_MB: int = 500
    BACKUP_RETENTION_COUNT: int = 7
    STORAGE_DIR: str = "./storage"
    DATA_DIR: str = "./data"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    DATABASE_URL: str = "sqlite:///./data/smartcloset.db"
    OPENAI_API_KEY: str | None = None
    OPENWEATHER_API_KEY: str | None = None
    DEFAULT_CITY: str = "Morioka"


settings = Settings()
