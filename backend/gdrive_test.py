from google.oauth2 import service_account
from googleapiclient.discovery import build

# Path to your JSON key
KEY_FILE = "gdrive_sa.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

creds = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
service = build("drive", "v3", credentials=creds)

# Replace with your folder ID
FOLDER_ID = "1kriplidT1FvKuFchYvouDRS1Scp_zKbW"

# List files in the folder
query = f"'{FOLDER_ID}' in parents"
result = service.files().list(q=query, fields="files(id, name)").execute()
items = result.get("files", [])

print("Files in folder:")
for item in items:
    print(f"{item['name']} ({item['id']})")
