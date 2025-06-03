# backend/main.py

import os
import io
import mimetypes
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy.exc import IntegrityError

from schemas import ParsedDocument, DealData
from db import init_db, SessionLocal, ParsedDeal

# Initialize DB tables
init_db()

app = FastAPI()

# ---------------------------
# Google Drive Setup
# ---------------------------

# Path to your service account JSON (make sure gdrive_sa.json is in /backend)
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
    Returns a list of dicts: [{"id": "...", "name": "..."}, ...].
    """
    files = []
    page_token = None
    query = f"'{folder_id}' in parents and trashed=false"
    while True:
        response = (
            drive_service.files()
            .list(q=query, spaces="drive", fields="nextPageToken, files(id, name, mimeType)", pageToken=page_token)
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
    fh = io.BytesIO()
    downloader = build("drive", "v3", credentials=creds).files().get_media(fileId=file_id)
    # Simpler approach:
    request = drive_service.files().get_media(fileId=file_id)
    dl = request.execute()
    return dl

def parse_pdf_bytes(pdf_bytes: bytes) -> ParsedDocument:
    """
    Extract text and tables from a PDF blob using unstructured.
    """
    from unstructured.partition.pdf import partition_pdf
    from unstructured.partition.common import convert_to_text

    # Write to a temp bytesIO so unstructured can read
    with io.BytesIO(pdf_bytes) as pdf_stream:
        # unstructured returns a list of elements; convert to text
        elements = partition_pdf(filename=None, file=pdf_stream)
        full_text = convert_to_text(elements)

    # For MVP, we won’t parse structured tables via Camelot.
    return ParsedDocument(
        filename="unknown.pdf",
        file_id="",  # to be set by caller
        text=full_text,
        tables=[],
    )

def parse_xlsx_bytes(xlsx_bytes: bytes) -> ParsedDocument:
    """
    Read an XLSX from bytes via pandas, convert each sheet to a list of row-dicts.
    """
    import pandas as pd

    # Read into a Pandas ExcelFile object using BytesIO
    from io import BytesIO
    xls = pd.ExcelFile(BytesIO(xlsx_bytes))
    tables = []
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name)
        # Convert each sheet’s DataFrame to list-of-dicts
        table_dicts = df.fillna("").to_dict(orient="records")
        tables.append({"sheet": sheet_name, "rows": table_dicts})

    return ParsedDocument(
        filename="unknown.xlsx",
        file_id="",
        text="",
        tables=tables,
    )

def parse_drive_file(file_meta: dict) -> ParsedDocument:
    """
    Download and parse a Google Drive file based on mimeType.
    """
    file_id = file_meta["id"]
    name = file_meta["name"]
    mime_type = file_meta.get("mimeType", "")
    blob = download_file(file_id, name)

    if mime_type == "application/pdf" or name.lower().endswith(".pdf"):
        parsed = parse_pdf_bytes(blob)
    elif "spreadsheet" in mime_type or name.lower().endswith((".xlsx", ".xls")):
        parsed = parse_xlsx_bytes(blob)
    else:
        # For any other file types (e.g. Word), simply extract text via unstructured, if possible
        from unstructured.partition.docx import partition_docx
        from unstructured.partition.common import convert_to_text
        with io.BytesIO(blob) as stream:
            try:
                elems = partition_docx(filename=None, file=stream)
                text = convert_to_text(elems)
                parsed = ParsedDocument(filename=name, file_id=file_id, text=text, tables=[])
            except Exception:
                parsed = ParsedDocument(filename=name, file_id=file_id, text="", tables=[])
    parsed.filename = name
    parsed.file_id = file_id
    return parsed

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

@app.post("/process-deal", response_model=ProcessResponse)
async def process_deal(req: ProcessRequest):
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
    for file_meta in files:
        try:
            parsed = parse_drive_file(file_meta)
            parsed_docs.append(parsed)
        except Exception as e:
            # Skip a file if parsing fails, but log it
            print(f"Failed to parse {file_meta['name']}: {e}")
            continue

    deal_data = DealData(deal_id=deal_id, documents=parsed_docs)

    # 2) Validate via Pydantic (already validated in models)
    #    Convert DealData to dict for insertion
    deal_dict = deal_data.dict()

    # 3) Save to Postgres JSONB
    session = SessionLocal()
    new_entry = ParsedDeal(deal_id=deal_id, data=deal_dict)
    try:
        session.add(new_entry)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Deal already exists.")
    finally:
        session.close()

    # 4) At this MVP stage, skip embedding creation. We'll add that next.
    return ProcessResponse(deal_id=deal_id, num_documents=len(parsed_docs))

# ---------------------------
# Remaining stubs (leave as before)
# ---------------------------

@app.get("/chat")
async def chat():
    return {"reply": "This is still a placeholder chat response."}

@app.get("/report/{deal_id}")
async def report(deal_id: str):
    return {"report": f"This is still a placeholder report for {deal_id}."}

@app.get("/health")
def health():
    return {"status": "ok"}
