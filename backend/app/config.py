from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CODEX_", env_file=".env")

    database_url: str = "postgresql+asyncpg://codex:codex@localhost:5432/codex"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    audiobookshelf_url: str = ""
    audiobookshelf_api_key: str = ""

    openlibrary_enabled: bool = True

    download_dir: Path = Path("/data/codex/downloads")
    temp_dir: Path = Path("/tmp/codex")


settings = Settings()
