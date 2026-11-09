import os
import sys
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_default_data_dir() -> Path:
    # 1. Environment variable override
    env_dir = os.environ.get("LSIA_DATA_DIR")
    if env_dir:
        return Path(env_dir)

    # 2. Local dev repository: if root/server exists, use dev root / "data"
    dev_root = Path(__file__).resolve().parents[2]
    if (dev_root / "server" / "pyproject.toml").exists() or (dev_root / ".git").exists():
        return dev_root / "data"

    # 3. Installed application on Windows: use %LOCALAPPDATA%\LSIA\data
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "LSIA" / "data"

    # 4. Fallback for other systems
    return Path.home() / ".local" / "share" / "lsia" / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LSIA_", env_file=".env", extra="ignore")

    school_id: str = "school-local"
    host: str = "0.0.0.0"
    port: int = 8080
    data_dir: Path = get_default_data_dir()
    database_url: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_hours: int = 12
    cors_origins: str = "*"
    public_base_url: str = "http://127.0.0.1:8080"

    def model_post_init(self, __context: Any) -> None:
        if not self.database_url:
            self.database_url = f"sqlite:///{self.data_dir / 'lsia.db'}"

    @property
    def keys_dir(self) -> Path:
        return self.data_dir / "keys"


settings = Settings()
