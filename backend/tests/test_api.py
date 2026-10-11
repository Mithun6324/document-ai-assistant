import os
from pathlib import Path

# Must set env before app imports
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["GEMINI_API_KEY"] = "test-key"
os.environ["CHROMA_PERSIST_DIR"] = str(Path("/tmp/docai_test_chroma"))
os.environ["UPLOAD_DIR"] = str(Path("/tmp/docai_test_uploads"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

get_settings.cache_clear()

from app.db.session import Base, get_db
from app.main import app


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_register_and_login(client):
    res = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "password123", "full_name": "Test"},
    )
    assert res.status_code == 200
    assert res.json()["email"] == "user@example.com"

    login = client.post("/auth/login", json={"email": "user@example.com", "password": "password123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert token

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


def test_login_invalid(client):
    client.post("/auth/register", json={"email": "a@b.com", "password": "password123"})
    res = client.post("/auth/login", json={"email": "a@b.com", "password": "wrongpass1"})
    assert res.status_code == 401


def test_upload_rejects_bad_type(client):
    client.post("/auth/register", json={"email": "u@test.com", "password": "password123"})
    token = client.post("/auth/login", json={"email": "u@test.com", "password": "password123"}).json()["access_token"]
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    res = client.post("/documents/upload", files=files, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400


def test_upload_rejects_empty(client):
    client.post("/auth/register", json={"email": "u2@test.com", "password": "password123"})
    token = client.post("/auth/login", json={"email": "u2@test.com", "password": "password123"}).json()["access_token"]
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    res = client.post("/documents/upload", files=files, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400


def test_cleaning_service():
    from app.services.cleaning_service import clean_text

    raw = "Hello   world\n\n\nPage 1 of 2\n\nConfidential\nSkills\nPython"
    cleaned = clean_text(raw)
    assert "Page 1 of 2" not in cleaned
    assert "Confidential" not in cleaned
    assert "Skills" in cleaned
    assert "  " not in cleaned


def test_chunk_service_preserves_sections():
    from app.services.chunk_service import semantic_chunk

    pages = [
        {
            "page_number": 1,
            "text": "Skills\nPython, FastAPI, SQL\n\nExperience\nBuilt RAG systems with FastAPI.",
        }
    ]
    chunks = semantic_chunk(pages, "doc-1", "resume.pdf")
    assert len(chunks) >= 1
    sections = {c.get("section_name") for c in chunks}
    assert "Skills" in sections or "Experience" in sections
