# backend/main.py

import os
import io
import mimetypes
from typing import List
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

import openai
from chromadb import Client
from chromadb.utils import embedding_functions

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy.exc import IntegrityError

from schemas import ParsedDocument, DealData
from db import init_db, SessionLocal, ParsedDeal

# ---------------------------
# Initialize DB tables
# ---------------------------

init_db()

app = FastAPI()

# ---------------------------
# OpenAI & Chroma Setup
# ---------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY in environment")

openai.api_key = OPENAI_API_KEY

# Connect to Chroma (HTTP API mode). The default URL is http://chroma:8000 in Docker.
chroma_client = Client()

# Create or get a collection named "deal_embeddings"
collection = chroma_client.get_or_create_collection(
    name="deal_embeddings",
    embedding_function=embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name="text-embedding-ada-002"
    ),
)

# ---------------------------
# Google Drive Setup
# ---------------------------

GDRIVE_CREDENTIALS_PATH = os.getenv("GDRIVE_CREDENTIALS_PATH", "gdrive_sa.json")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

creds = service_account.Credentials.from_service_account_file(
    GDRIVE_CREDENTIALS_PATH, scopes=SCOPES
)
drive_service = build("drive", "v3", credentials=creds)

# ---------------------------
# Helper functions
# ---------------------------

def list_drive_files(folder_id: str):
    """
    Retrieve all files in the given Google Drive folder.
    Returns a list of dicts: [{"id": "...", "name": "...", "mimeType": "..."}].
    """
    files = []
    page_token = None
    query = f"'{folder_id}' in parents and trashed=false"
    while True:
        response = (
            drive_service.files()
            .list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page_token
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken", None)
        if page_token is None:
            break
    return files

def download_file(file_id: str, filename: str) -> bytes:
    """
    Download a file’s content as bytes.
    """
    request = drive_service.files().get_media(fileId=file_id)
    return request.execute()

def parse_pdf_bytes(pdf_bytes: bytes) -> ParsedDocument:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.partition.common import convert_to_text

    with io.BytesIO(pdf_bytes) as pdf_stream:
        elements = partition_pdf(filename=None, file=pdf_stream)
        full_text = convert_to_text(elements)

    return ParsedDocument(
        filename="unknown.pdf",
        file_id="",
        text=full_text,
        tables=[],
        cashflow=[],
        debt_schedule=[]
    )

def parse_xlsx_bytes(xlsx_bytes: bytes) -> ParsedDocument:
    import pandas as pd
    from io import BytesIO

    xls = pd.ExcelFile(BytesIO(xlsx_bytes))
    tables = []
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name)
        table_dicts = df.fillna("").to_dict(orient="records")
        tables.append({"sheet": sheet_name, "rows": table_dicts})

    return ParsedDocument(
        filename="unknown.xlsx",
        file_id="",
        text="",
        tables=tables,
        cashflow=[],
        debt_schedule=[]
    )


def parse_drive_file(file_meta: dict) -> ParsedDocument:
    """
    Download and parse a Google Drive file based on mimeType.
    Returns a ParsedDocument. Unsupported types are returned as empty-text docs.
    """

    file_id = file_meta["id"]
    name = file_meta["name"]
    mime_type = file_meta.get("mimeType", "")

    # 1) Skip GDrive sub-folders
    if mime_type == "application/vnd.google-apps.folder":
        # Return an essentially empty ParsedDocument
        return ParsedDocument(
            filename=name,
            file_id=file_id,
            text="",
            tables=[],
            cashflow=[],
            debt_schedule=[]
        )

    # 2) Download bytes
    blob = download_file(file_id, name)

    # 3) Dispatch based on mimeType and extension
    if mime_type == "application/pdf" or name.lower().endswith(".pdf"):
        parsed = parse_pdf_bytes(blob)
    elif (
        "spreadsheet" in mime_type
        or name.lower().endswith((".xlsx", ".xls"))
    ):
        parsed = parse_xlsx_bytes(blob)
    elif (
        "document" in mime_type  # covers both docx and docm
        or name.lower().endswith((".docx", ".docm"))
    ):
        # Try unstructured's docx parser; if that fails, return empty
        try:
            from unstructured.partition.docx import partition_docx
            from unstructured.partition.common import convert_to_text

            with io.BytesIO(blob) as stream:
                elems = partition_docx(filename=None, file=stream)
                text = convert_to_text(elems)
            parsed = ParsedDocument(
                filename=name,
                file_id=file_id,
                text=text,
                tables=[],
                cashflow=[],
                debt_schedule=[]
            )
        except Exception:
            parsed = ParsedDocument(
                filename=name,
                file_id=file_id,
                text="",
                tables=[],
                cashflow=[],
                debt_schedule=[]
            )
    else:
        # 4) Unsupported types (images, plain text, etc.) → return empty
        parsed = ParsedDocument(
            filename=name,
            file_id=file_id,
            text="",
            tables=[],
            cashflow=[],
            debt_schedule=[]
        )

    # 5) Ensure filename/file_id are set
    parsed.filename = name
    parsed.file_id = file_id
    return parsed

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into semi‐overlapping chunks of roughly chunk_size characters.
    Returns a list of text chunks.
    """
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

# ---------------------------
# API Models
# ---------------------------

class ProcessRequest(BaseModel):
    folder_id: str

class ProcessResponse(BaseModel):
    deal_id: str
    num_documents: int

# ---------------------------
# `/process-deal` endpoint
# ---------------------------

@app.post("/process-deal")
async def process_deal_debug(req: ProcessRequest):
    folder_id = req.folder_id
    deal_id = f"deal_{folder_id}_{int(datetime.utcnow().timestamp())}"

    # 1) List files in the folder
    try:
        files = list_drive_files(folder_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error listing Drive folder: {e}")

    if not files:
        raise HTTPException(status_code=404, detail="No files found in the specified folder.")

    parsed_docs: List[ParsedDocument] = []
    parsed_filenames: List[str] = []
    failed_filenames: List[str] = []

    for file_meta in files:
        name = file_meta["name"]
        try:
            parsed = parse_drive_file(file_meta)
            parsed_docs.append(parsed)
            parsed_filenames.append(name)
        except Exception as e:
            # Log the failure and keep going
            failed_filenames.append(f"{name}: {e}")
            continue

    # Return debug info instead of full logic
    return {
        "folder_id": folder_id,
        "all_files": [f["name"] for f in files],
        "parsed_files": parsed_filenames,
        "failed": failed_filenames,
        "num_parsed": len(parsed_docs)
    }

# ---------------------------
# Remaining stubs
# ---------------------------

@app.post("/chat")
async def chat():
    return {"reply": "This is still a placeholder chat response."}

@app.get("/report/{deal_id}")
async def report(deal_id: str):
    return {"report": f"This is still a placeholder report for {deal_id}."}

@app.get("/health")
def health():
    return {"status": "ok"}
