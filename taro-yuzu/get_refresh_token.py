#!/usr/bin/env python3
"""One-time: get a YouTube refresh token for the uploader. Run this on YOUR computer (it opens a browser).

  python3 get_refresh_token.py path/to/client_secret.json

Needs only Python 3.8+ (no packages). The client_secret.json is the "Desktop app" OAuth client you download
from Google Cloud Console (SETUP.md §3). Sign in with the Google account that owns the Taro & Yuzu channel
and, if asked, pick the channel (brand account) — not your personal one.

It prints three values to paste into GitHub → Settings → Secrets and variables → Actions:
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
"""
import base64
import hashlib
import http.server
import json
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser

SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube"
AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1]) as f:
        raw = json.load(f)
    c = raw.get("installed") or raw.get("web") or raw
    client_id, client_secret = c["client_id"], c["client_secret"]

    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state and "code" in q:
                result["code"] = q["code"][0]
                msg = "Done. You can close this tab and go back to the terminal."
            else:
                result["error"] = q.get("error", ["unknown"])[0]
                msg = "Something went wrong: " + result["error"]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(msg.encode())

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect = f"http://127.0.0.1:{srv.server_port}/"
    url = AUTH + "?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
        "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })
    print("Opening your browser to sign in. If it doesn't open, paste this URL into it:\n\n" + url + "\n")
    webbrowser.open(url)
    while "code" not in result and "error" not in result:
        srv.handle_request()
    if "error" in result:
        sys.exit("Sign-in failed: " + result["error"])

    data = urllib.parse.urlencode({
        "code": result["code"], "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": verifier,
    }).encode()
    with urllib.request.urlopen(urllib.request.Request(TOKEN, data=data)) as r:
        tok = json.load(r)
    if "refresh_token" not in tok:
        sys.exit("No refresh token came back. Remove the app's access at https://myaccount.google.com/permissions and run again.")
    print("Paste these three into GitHub → your repo → Settings → Secrets and variables → Actions → New repository secret:\n")
    print("YT_CLIENT_ID     =", client_id)
    print("YT_CLIENT_SECRET =", client_secret)
    print("YT_REFRESH_TOKEN =", tok["refresh_token"])
    print("\nKeep them private. Anyone with all three can upload to your channel.")


if __name__ == "__main__":
    main()
