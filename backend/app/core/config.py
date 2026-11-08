from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'todo.db'}"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    xp_task_points: int = Field(default=10, ge=0)
    xp_daily_cap: int = Field(default=100, gt=0)
    xp_bonus_half: int = Field(default=10, ge=0)
    xp_bonus_full: int = Field(default=20, ge=0)
    xp_level_step: int = Field(default=100, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
