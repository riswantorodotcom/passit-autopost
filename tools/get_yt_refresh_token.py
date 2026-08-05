#!/usr/bin/env python3
# Jalankan DI KOMPUTERMU (sekali saja) untuk dapat YouTube refresh token.
#   pip install google-auth-oauthlib
#   set YT_CLIENT_ID / YT_CLIENT_SECRET dari OAuth client (tipe "Desktop app")
#   python tools/get_yt_refresh_token.py
# Browser akan terbuka -> login channel PASSit -> setujui. Token dicetak ke layar.
import os
from google_auth_oauthlib.flow import InstalledAppFlow
CID = os.environ.get("YT_CLIENT_ID") or input("YT_CLIENT_ID: ").strip()
CSEC = os.environ.get("YT_CLIENT_SECRET") or input("YT_CLIENT_SECRET: ").strip()
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
flow = InstalledAppFlow.from_client_config({"installed": {
    "client_id": CID, "client_secret": CSEC,
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["http://localhost"]}}, SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
print("\n=== SIMPAN INI sebagai GitHub Secret YT_REFRESH_TOKEN ===")
print(creds.refresh_token)
