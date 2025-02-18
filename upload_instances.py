import requests
import hashlib
from datetime import datetime
import os
import time

# GitHub and Azure Config
GITHUB_REPO = os.environ.get("GH_REPO")
FILE_PATH = os.environ.get("FILE_PATH")
AZURE_BLOB_URL = os.environ.get("AZURE_BLOB_URL")
AZURE_SAS_TOKEN = os.environ.get("AZURE_SAS_TOKEN")

# GitHub API URL for commits
COMMITS_URL = f"https://api.github.com/repos/{GITHUB_REPO.replace('https://github.com/', '')}/commits?path={FILE_PATH}"

# Cache files
LAST_COMMIT_FILE = "last_commit.txt"
LAST_HASH_FILE = "last_file_hash.txt"
LOCK_FILE = "upload.lock"

def get_last_commit():
    """Retrieve the last commit hash from the cache."""
    if os.path.exists(LAST_COMMIT_FILE):
        with open(LAST_COMMIT_FILE, "r") as file:
            return file.read().strip()
    return None

def save_last_commit(commit_hash):
    """Save the latest commit hash to the cache."""
    with open(LAST_COMMIT_FILE, "w") as file:
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

def calculate_file_hash(file_path):
    """Calculate SHA256 hash of the file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_last_file_hash():
    """Retrieve the last known file hash."""
    if os.path.exists(LAST_HASH_FILE):
        with open(LAST_HASH_FILE, "r") as file:
            return file.read().strip()
    return None

def save_last_file_hash(file_hash):
    """Save the last file hash."""
    with open(LAST_HASH_FILE, "w") as file:
        file.write(file_hash)

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
        print(f"✅ Uploaded {file_path} to Azure Blob Storage.")
    else:
        print(f"❌ Failed to upload file: {response.status_code}, {response.text}")

def acquire_lock():
    """Acquire a lock to prevent concurrent runs."""
    if os.path.exists(LOCK_FILE):
        print("🔒 Lock file exists. Another process might be running. Exiting.")
        return False
    with open(LOCK_FILE, "w") as file:
        file.write(str(time.time()))
    return True

def release_lock():
    """Release the lock."""
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

def main():
    if not acquire_lock():
        return

    try:
        latest_commit, commit_date = get_latest_commit()

        if latest_commit:
            print(f"🆕 Checking commit: {latest_commit} from {commit_date}")

            # Construct raw GitHub URL to download the file
            raw_url = f"{GITHUB_REPO}/raw/main/{FILE_PATH}"
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            save_path = f"instances_{timestamp}.json"

            if download_file(raw_url, save_path):
                # Calculate the new file's hash
                new_hash = calculate_file_hash(save_path)
                old_hash = get_last_file_hash()

                if new_hash != old_hash:
                    # Only upload if content changed
                    upload_to_azure_with_sas(save_path)
                    save_last_commit(latest_commit)
                    save_last_file_hash(new_hash)
                else:
                    print("⚠️ File content has not changed. Skipping upload.")
                    os.remove(save_path)  # Clean up downloaded file if unchanged
            else:
                print("❌ Failed to download file.")
        else:
            print("🔍 No new commits found.")

    finally:
        release_lock()

if __name__ == "__main__":
    main()

