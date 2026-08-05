#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Direct Post reels/latest/reel.mp4 ke TikTok (Content Posting API, FILE_UPLOAD).
No-op kalau credential belum diset. Default privacy SELF_ONLY (aman sebelum audit lolos);
setelah audit, set secret TIKTOK_PRIVACY=PUBLIC_TO_EVERYONE."""
import os, sys, time, requests
REQ = ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"]
if not all(os.environ.get(k) for k in REQ):
    print("[tiktok] credential (TIKTOK_CLIENT_KEY/SECRET/REFRESH_TOKEN) belum diset — skip."); sys.exit(0)

ROOT = os.path.dirname(os.path.abspath(__file__))
video = os.path.join(ROOT, "reels", "latest", "reel.mp4")
if not os.path.exists(video):
    sys.exit("Tidak ada reels/latest/reel.mp4")
cap = ""
cp = os.path.join(ROOT, "reels", "latest", "caption.txt")
if os.path.exists(cp):
    cap = open(cp, encoding="utf-8").read().strip()
title = cap[:2150] if cap else "Tips belajar #belajar"

# 1) refresh access token
r = requests.post("https://open.tiktokapis.com/v2/oauth/token/",
    data={"client_key": os.environ["TIKTOK_CLIENT_KEY"],
          "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
          "grant_type": "refresh_token",
          "refresh_token": os.environ["TIKTOK_REFRESH_TOKEN"]},
    headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=60).json()
at = r.get("access_token")
if not at:
    sys.exit(f"TikTok token error: {r}")

size = os.path.getsize(video)
h = {"Authorization": "Bearer " + at, "Content-Type": "application/json; charset=UTF-8"}
init = {
    "post_info": {"title": title,
                  "privacy_level": os.environ.get("TIKTOK_PRIVACY", "SELF_ONLY"),
                  "disable_comment": False, "disable_duet": False, "disable_stitch": False},
    "source_info": {"source": "FILE_UPLOAD", "video_size": size,
                    "chunk_size": size, "total_chunk_count": 1},
}
r = requests.post("https://open.tiktokapis.com/v2/post/publish/video/init/",
                  json=init, headers=h, timeout=60).json()
d = r.get("data", {}) or {}
upurl = d.get("upload_url"); pubid = d.get("publish_id")
if not upurl:
    sys.exit(f"TikTok init error: {r}")

# 2) upload bytes (single chunk)
data = open(video, "rb").read()
put = requests.put(upurl, data=data, headers={
    "Content-Type": "video/mp4",
    "Content-Length": str(size),
    "Content-Range": f"bytes 0-{size-1}/{size}"}, timeout=180)
print("[tiktok] upload HTTP", put.status_code)

# 3) poll status
for i in range(24):
    s = requests.post("https://open.tiktokapis.com/v2/post/publish/status/fetch/",
                      json={"publish_id": pubid}, headers=h, timeout=60).json()
    st = (s.get("data", {}) or {}).get("status")
    print(f"  status[{i}]: {st}")
    if st in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
        break
    if st in ("FAILED",):
        sys.exit(f"TikTok gagal: {s}")
    time.sleep(5)
print("[tiktok] selesai, publish_id:", pubid,
      "| privacy:", init["post_info"]["privacy_level"])
