import os
import importlib
import sys
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import googleapiclient.discovery
import chromadb
from google.oauth2 import service_account

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "backend"))

# Patch environment and heavy dependencies before importing the app
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("POSTGRES_USER", "user")
os.environ.setdefault("POSTGRES_PASSWORD", "pw")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_DB", "deals")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("GDRIVE_CREDENTIALS_PATH", "backend/gdrive_sa.json")

fake_drive_service = MagicMock()
files_service = MagicMock()
files_service.list.return_value.execute.return_value = {"files": []}
fake_drive_service.files.return_value = files_service

chromadb_client = MagicMock()
chromadb_client.get_or_create_collection.return_value = MagicMock()

def build_stub(*args, **kwargs):
    return fake_drive_service

def client_stub(*args, **kwargs):
    return chromadb_client

# Apply patches before importing backend.main
mp = pytest.MonkeyPatch()
mp.setattr(googleapiclient.discovery, "build", build_stub)
mp.setattr(chromadb, "Client", client_stub)
mp.setattr(
    service_account.Credentials,
    "from_service_account_file",
    lambda *args, **kwargs: MagicMock(),
)
import db  # module resolved from backend/db.py
import backend.db as backend_db
mp.setattr(db, "init_db", lambda: None)
mp.setattr(backend_db, "init_db", lambda: None)

app_module = importlib.import_module("backend.main")
client = TestClient(app_module.app)

@pytest.fixture
def test_client():
    yield client


def test_health(test_client):
    resp = test_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_process_deal(test_client):
    from backend import routes as app_routes
    from backend.schemas import ParsedDocument

    def mock_list(folder_id: str):
        return [
            {"id": "1", "name": "doc1.pdf", "mimeType": "application/pdf"},
            {
                "id": "2",
                "name": "sheet.xlsx",
                "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
        ]

    def mock_parse(file_meta):
        return ParsedDocument(
            filename=file_meta["name"],
            file_id=file_meta["id"],
            text="dummy",
            tables=[],
            cashflow=[],
            debt_schedule=[],
        )

    mp.setattr(app_routes, "list_drive_files", mock_list)
    mp.setattr(app_routes, "parse_drive_file", mock_parse)

    resp = test_client.post("/process-deal", json={"folder_id": "F1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["deal_id"].startswith("deal_F1_")
    assert data["num_documents"] == 2


def test_chat_placeholder(test_client):
    resp = test_client.post("/chat")
    assert resp.status_code == 200
    assert resp.json() == {"reply": "This is still a placeholder chat response."}


def test_report_placeholder(test_client):
    deal_id = "D123"
    resp = test_client.get(f"/report/{deal_id}")
    assert resp.status_code == 200
    assert resp.json() == {"report": f"This is still a placeholder report for {deal_id}."}
