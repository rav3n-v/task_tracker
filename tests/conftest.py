from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app, db


@pytest.fixture()
def app(tmp_path):
    database_path = tmp_path / "test_tracker.db"
    flask_app = create_app()
    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
        SECRET_KEY="test-secret",
    )

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

    yield flask_app

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(client):
    client.post('/api/register', json={'username': 'alice', 'password': 'password123'})
    return client
