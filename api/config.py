"""api/config.py — environment configuration via Pydantic Settings.

Reads from .env at the project root (the same .env the CLI uses for
GROQ_API_KEY) so configuration stays in one file. Pydantic Settings
gives us type-safe env vars and a single Settings() instance to import
elsewhere — no os.environ.get scattered through the codebase.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).parent.parent  # one level up from api/


class Settings(BaseSettings):
    """All env-driven configuration in one place.

    DATABASE_URL is required in the schema (so an operator can't
    accidentally deploy with no DB configured), but the database is
    NOT actually connected at startup — see api/database.py for the
    lazy-connection design."""

    database_url: str = "postgresql+psycopg2://studyrag:studyrag@localhost:5432/studyrag"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    debug: bool = False
    studyrag_db_path: str = r"C:\Users\91460\OneDrive\Desktop\studpart\data\chroma_db"

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_prefix="STUDYRAG_",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# One module-level instance. Imported as `from api.config import settings`.
settings = Settings()
