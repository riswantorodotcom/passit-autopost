#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upload reels/latest/reel.mp4 sebagai YouTube Short. No-op kalau credential belum diset."""
import os, sys, glob
REQ = ["YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"]
if not all(os.environ.get(k) for k in REQ):
    print("[youtube] credential (YT_CLIENT_ID/SECRET/REFRESH_TOKEN) belum diset — skip."); sys.exit(0)

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = os.path.dirname(os.path.abspath(__file__))
video = os.path.join(ROOT, "reels", "latest", "reel.mp4")
if not os.path.exists(video):
    sys.exit("Tidak ada reels/latest/reel.mp4")
cap = ""
cp = os.path.join(ROOT, "reels", "latest", "caption.txt")
if os.path.exists(cp):
    cap = open(cp, encoding="utf-8").read().strip()

first = next((l.strip() for l in cap.splitlines() if l.strip()), "PASSit.id — tips belajar")
title = first[:80].rstrip()
if "#shorts" not in title.lower():
    title = (title + " #Shorts")[:100]
desc = (cap + "\n\n#Shorts #belajar #tipsbelajar").strip()[:4900]

creds = Credentials(None,
    refresh_token=os.environ["YT_REFRESH_TOKEN"],
    client_id=os.environ["YT_CLIENT_ID"],
    client_secret=os.environ["YT_CLIENT_SECRET"],
    token_uri="https://oauth2.googleapis.com/token")
yt = build("youtube", "v3", credentials=creds)

body = {
    "snippet": {"title": title, "description": desc, "categoryId": "27",
                "tags": ["belajar", "tips belajar", "edukasi", "shorts", "study tips"]},
    "status": {"privacyStatus": os.environ.get("YT_PRIVACY", "public"),
               "selfDeclaredMadeForKids": False},
}
media = MediaFileUpload(video, mimetype="video/mp4", resumable=True)
req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
resp = None
while resp is None:
    status, resp = req.next_chunk()
print("[youtube] OK, video id:", resp.get("id"), "| privacy:", body["status"]["privacyStatus"])
