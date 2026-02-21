from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "AtlasAgent"
    redis_url: str = "redis://localhost:6379/0"
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()
