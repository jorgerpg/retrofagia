from pydantic_settings import BaseSettings


class Settings(BaseSettings):

  POSTGRES_USER: str = "retrofagia"
  POSTGRES_PASSWORD: str = "retrofagia_pw"
  POSTGRES_DB: str = "retrofagia"
  POSTGRES_HOST: str = "db"
  POSTGRES_PORT: int = 5432

  BACKEND_CORS_ORIGINS: str = "http://localhost:3000"
  JWT_SECRET: str = "change"
  JWT_ALG: str = "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

  @property
  def database_url(self) -> str:
    return (
        f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
        f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    )


settings = Settings()
