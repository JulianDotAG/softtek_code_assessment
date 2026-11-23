from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from the environment or a local .env file.

    The DSNs carry no user or password on purpose: libpq falls back to the OS user,
    which keeps the repository runnable on any machine without editing config.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost:5432/softtek_assessment"
    test_database_url: str = "postgresql+psycopg://localhost:5432/softtek_assessment_test"


settings = Settings()
