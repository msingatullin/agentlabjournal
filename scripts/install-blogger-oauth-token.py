#!/usr/bin/env python3
"""Validate and atomically install Blogger OAuth credentials without echoing secrets."""
from getpass import getpass
from pathlib import Path
from urllib.error import HTTPError, URLError
import json
import os
import tempfile
import urllib.parse
import urllib.request

TOKEN_FILE = Path(os.environ.get("BLOGGER_TOKEN_FILE", "/root/.config/blogger-token.json"))
TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/blogger"


def hidden(label: str) -> str:
    value = getpass(label).strip()
    if not value:
        raise SystemExit(f"{label.rstrip(': ')} is empty")
    return value


client_id = hidden("New client ID: ")
client_secret = hidden("New client secret: ")
refresh_token = hidden("New refresh token: ")

request_data = urllib.parse.urlencode(
    {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
).encode()
request = urllib.request.Request(
    TOKEN_URI,
    data=request_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        refreshed = json.loads(response.read())
except HTTPError as error:
    try:
        detail = json.loads(error.read().decode("utf-8", "replace"))
        reason = detail.get("error_description") or detail.get("error") or "unknown OAuth error"
    except (json.JSONDecodeError, UnicodeDecodeError):
        reason = "OAuth endpoint rejected the credentials"
    raise SystemExit(f"Validation failed (HTTP {error.code}): {reason}")
except URLError as error:
    raise SystemExit(f"Validation failed: {error.reason}")

if not refreshed.get("access_token"):
    raise SystemExit("Validation failed: Google did not return an access token")

document = {
    "client_id": client_id,
    "client_secret": client_secret,
    "refresh_token": refresh_token,
    "token_uri": TOKEN_URI,
    "scope": refreshed.get("scope", SCOPE),
    "token_type": refreshed.get("token_type", "Bearer"),
    "expires_in": refreshed.get("expires_in"),
}
if refreshed.get("refresh_token_expires_in") is not None:
    document["refresh_token_expires_in"] = refreshed["refresh_token_expires_in"]

TOKEN_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
fd, temporary_name = tempfile.mkstemp(prefix=".blogger-token-", dir=TOKEN_FILE.parent)
try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump(document, output, ensure_ascii=False, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary_name, TOKEN_FILE)
    os.chmod(TOKEN_FILE, 0o600)
except BaseException:
    try:
        os.unlink(temporary_name)
    except FileNotFoundError:
        pass
    raise

expiry = document.get("refresh_token_expires_in")
if expiry is None:
    print("Blogger OAuth credentials installed and validated; no refresh-token expiry was returned.")
else:
    print(f"Blogger OAuth credentials installed, but refresh token is time-limited to {expiry} seconds.")
