import requests
import hashlib
from datetime import datetime
import os

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

