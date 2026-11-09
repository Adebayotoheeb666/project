from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lsia.config import settings
from lsia.infrastructure import db
from lsia.main import create_app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-please-use-32-bytes!!")
    settings.data_dir = tmp_path
    settings.jwt_secret = "test-secret-please-use-32-bytes!!"
    settings.database_url = f"sqlite:///{tmp_path / 'lsia.db'}"
    db.configure_engine(settings.database_url)
    db.Base.metadata.drop_all(bind=db.engine)
    db.Base.metadata.create_all(bind=db.engine)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
