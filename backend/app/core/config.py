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

    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = True

settings = Settings()