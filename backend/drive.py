import os
from typing import List, Dict

from google.oauth2 import service_account
from googleapiclient.discovery import build

# Google Drive API setup
GDRIVE_CREDENTIALS_PATH = os.getenv("GDRIVE_CREDENTIALS_PATH", "gdrive_sa.json")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

creds = service_account.Credentials.from_service_account_file(
    GDRIVE_CREDENTIALS_PATH, scopes=SCOPES
)
drive_service = build("drive", "v3", credentials=creds)


def list_drive_files(folder_id: str) -> List[Dict[str, str]]:
    """Return non-trashed files within the given Drive folder."""
    files: List[Dict[str, str]] = []
    page_token: str | None = None
    query = f"'{folder_id}' in parents and trashed=false"
    while True:
        response = (
            drive_service.files()
            .list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page_token,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if page_token is None:
            break
    return files


def download_file(file_id: str, filename: str) -> bytes:
    """Download a file's bytes from Google Drive."""
    request = drive_service.files().get_media(fileId=file_id)
    return request.execute()
