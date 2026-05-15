from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "pythonChat"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DB_USER: str = "pythonchatdb"
    DB_PASSWORD: str = "zs4FhGa5jZMb6b"
    DB_HOST: str = "10.20.10.10"
    DB_PORT: int = 5432
    DB_NAME: str = "python"
    DB_SCHEMA: str = "chat"

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    ALLOWED_ORIGINS: str = "*"

    ALLOW_REGISTRATION: bool = True

    COOKIE_SECURE: bool = False

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"


settings = Settings()
