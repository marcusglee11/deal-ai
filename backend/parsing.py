import io
from typing import List

from .drive import download_file
from .schemas import ParsedDocument


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
        debt_schedule=[],
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
        debt_schedule=[],
    )


def parse_drive_file(file_meta: dict) -> ParsedDocument:
    """Download and parse a Google Drive file based on its mime type."""

    file_id = file_meta["id"]
    name = file_meta["name"]
    mime_type = file_meta.get("mimeType", "")

    if mime_type == "application/vnd.google-apps.folder":
        return ParsedDocument(
            filename=name,
            file_id=file_id,
            text="",
            tables=[],
            cashflow=[],
            debt_schedule=[],
        )

    blob = download_file(file_id, name)

    if mime_type == "application/pdf" or name.lower().endswith(".pdf"):
        parsed = parse_pdf_bytes(blob)
    elif "spreadsheet" in mime_type or name.lower().endswith((".xlsx", ".xls")):
        parsed = parse_xlsx_bytes(blob)
    elif "document" in mime_type or name.lower().endswith((".docx", ".docm")):
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
                debt_schedule=[],
            )
        except Exception:
            parsed = ParsedDocument(
                filename=name,
                file_id=file_id,
                text="",
                tables=[],
                cashflow=[],
                debt_schedule=[],
            )
    else:
        parsed = ParsedDocument(
            filename=name,
            file_id=file_id,
            text="",
            tables=[],
            cashflow=[],
            debt_schedule=[],
        )

    parsed.filename = name
    parsed.file_id = file_id
    return parsed


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks
