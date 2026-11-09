from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    school_id: str = "school-local"
    host: str = "0.0.0.0"
    port: int = 8080
    database_url: str = f"sqlite:///{ROOT / 'data' / 'lsia.db'}"
    data_dir: Path = ROOT / "data"
    jwt_secret: str = "change-me-in-production"
    jwt_hours: int = 12
    cors_origins: str = "*"
    public_base_url: str = "http://127.0.0.1:8080"

    @property
    def keys_dir(self) -> Path:
        return self.data_dir / "keys"


settings = Settings()
