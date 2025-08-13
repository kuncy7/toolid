from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "ToolID"
    APP_VERSION: str = "0.2.0"
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8
    DATABASE_URL: str = "sqlite:///./toolid.db"
    CORS_ALLOW_ORIGINS: str = "*"

    class Config:
        env_file = ".env"

settings = Settings()
