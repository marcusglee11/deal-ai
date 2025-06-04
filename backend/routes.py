from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .drive import list_drive_files
from .parsing import parse_drive_file
from .schemas import ParsedDocument

router = APIRouter()


class ProcessRequest(BaseModel):
    folder_id: str


class ProcessResponse(BaseModel):
    deal_id: str
    num_documents: int


@router.post("/process-deal")
async def process_deal_debug(req: ProcessRequest):
    folder_id = req.folder_id
    deal_id = f"deal_{folder_id}_{int(datetime.utcnow().timestamp())}"

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
            failed_filenames.append(f"{name}: {e}")
            continue

    response = ProcessResponse(deal_id=deal_id, num_documents=len(parsed_docs))
    return response


@router.post("/chat")
async def chat():
    return {"reply": "This is still a placeholder chat response."}


@router.get("/report/{deal_id}")
async def report(deal_id: str):
    return {"report": f"This is still a placeholder report for {deal_id}."}


@router.get("/health")
def health():
    return {"status": "ok"}
