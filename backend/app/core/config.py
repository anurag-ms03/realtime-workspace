from pathlib import Path
from pydantic_settings import BaseSettings

# Always resolve .env relative to this file's location
ENV_FILE = Path(__file__).parent.parent.parent / ".env"
class Settings(BaseSettings):
    # App
    APP_NAME: str = "Realtime Workspace API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # RabbitMQ
    RABBITMQ_URL: str

    # Celery
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = True

    def model_post_init(self, __context) -> None:
        # Default Celery to reuse existing RabbitMQ/Redis if not explicitly set
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.RABBITMQ_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL

settings = Settings()