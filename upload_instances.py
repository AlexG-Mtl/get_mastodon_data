import requests
import json
from datetime import datetime
from azure.storage.blob import BlobServiceClient
import os

# GitHub and Azure Config
GITHUB_REPO = os.environ.get("GH_REPO")
FILE_PATH = os.environ.get("FILE_PATH")
AZURE_BLOB_URL = os.environ.get("AZURE_BLOB_URL")
AZURE_SAS_TOKEN = os.environ.get("AZURE_SAS_TOKEN")
CONTAINER_NAME = "mastodon"

# GitHub API URL for commits
COMMITS_URL = f"https://api.github.com/repos/{GITHUB_REPO.replace('https://github.com/', '')}/commits?path={FILE_PATH}"

# Cache file to track last commit
CACHE_FILE = "last_commit.txt"

def get_last_commit():
    """Retrieve the last commit hash from the cache."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            return file.read().strip()
    return None

def save_last_commit(commit_hash):
    """Save the latest commit hash to the cache."""
    with open(CACHE_FILE, "w") as file:
        file.write(commit_hash)

def get_latest_commit():
    """Fetch the latest commit hash for the file."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    response = requests.get(COMMITS_URL, headers=headers)
    if response.status_code == 200:
        commits = response.json()
        if commits:
            return commits[0]['sha'], commits[0]['commit']['committer']['date']
    return None, None

def download_file(raw_url, save_path):
    """Download the file from the raw GitHub URL."""
    response = requests.get(raw_url)
    if response.status_code == 200:
        with open(save_path, "wb") as file:
            file.write(response.content)
        return True
    return False

def upload_to_azure_with_sas(file_path):
    """Upload the file to Azure Blob Storage using SAS token."""
    blob_name = os.path.basename(file_path)
    upload_url = f"{AZURE_BLOB_URL}/{blob_name}?{AZURE_SAS_TOKEN}"

    # Upload the file
    with open(file_path, 'rb') as file_data:
        response = requests.put(upload_url, data=file_data, headers={'x-ms-blob-type': 'BlockBlob'})
        
    if response.status_code == 201:
        print(f"Uploaded {file_path} to Azure Blob Storage successfully.")
    else:
        print(f"Failed to upload file: {response.status_code}, {response.text}")

def main():
    last_commit = get_last_commit()
    latest_commit, commit_date = get_latest_commit()

    if latest_commit and latest_commit != last_commit:
        print(f"New commit found: {latest_commit} from {commit_date}")

        # Construct raw GitHub URL to download the file
        raw_url = f"{GITHUB_REPO}/raw/main/{FILE_PATH}"
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        save_path = f"instances_{timestamp}.json"

        if download_file(raw_url, save_path):
            upload_to_azure_with_sas(save_path)
            save_last_commit(latest_commit)
        else:
            print("Failed to download file.")
    else:
        print("No new commits found.")

if __name__ == "__main__":
    main()
