import os
import sys
from unittest.mock import MagicMock

import googleapiclient.discovery
from google.oauth2 import service_account

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "backend"))

# Stub GDrive credentials and client creation to avoid filesystem/network deps
googleapiclient.discovery.build = lambda *a, **kw: MagicMock()
service_account.Credentials.from_service_account_file = lambda *a, **kw: MagicMock()

from backend.parsing import chunk_text


def test_chunk_text_overlap():
    text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    chunks = chunk_text(text, chunk_size=10, overlap=4)
    assert chunks == [
        "ABCDEFGHIJ",
        "GHIJKLMNOP",
        "MNOPQRSTUV",
        "STUVWXYZ",
        "YZ",
    ]

