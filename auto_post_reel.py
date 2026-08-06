#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_post_reel.py — posting REEL (video 9:16) PASSit ke Instagram Reels (+ Facebook Page video).
Video di-host dari repo ini via CDN jsDelivr (pakai commit SHA agar tidak kena cache basi).
Terpisah dari auto_post.py (carousel) — tidak saling mengganggu.

TAHAN-BANTING (v2):
  - Retry berlapis dengan backoff untuk tiap panggilan Meta (container, publish, FB).
    Kegagalan transient (mis. OAuthException code 200 "on behalf of user", video masih
    diproses, jaringan nge-blip) otomatis dicoba ulang beberapa kali sebelum menyerah.
  - Idempoten: setelah IG Reel berhasil dipublish, ditulis MARKER di /tmp. Kalau script
    dijalankan lagi dalam runner yang sama (mis. retry di level workflow), publish TIDAK
    diulang -> aman dari double-post.

Env (dari GitHub Secrets via workflow):
  IG_USER_ID, PAGE_ACCESS_TOKEN, PAGE_ID (opsional), POST_TO_FACEBOOK, GRAPH_VERSION
  GITHUB_REPOSITORY, GITHUB_SHA (otomatis), DRY_RUN (opsional), FB_ONLY (opsional)
  MAX_RETRIES (default 4), RETRY_BACKOFF (default 8 detik), PUBLISH_MARKER (opsional)
Sumber: reels/latest/<sesuatu>.mp4 + reels/latest/caption.txt
"""
import os, sys, glob, time, tempfile, requests

REPO   = os.environ["GITHUB_REPOSITORY"]
SHA    = os.environ.get("GITHUB_SHA", "main")
IG     = os.environ["IG_USER_ID"]
TOKEN  = os.environ["PAGE_ACCESS_TOKEN"]
PAGEID = os.environ.get("PAGE_ID", "")
POSTFB = os.environ.get("POST_TO_FACEBOOK", "true").lower() == "true"
V      = os.environ.get("GRAPH_VERSION", "v21.0")
DRY    = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
FB_ONLY= os.environ.get("FB_ONLY", "").lower() in ("1", "true", "yes")

RETRIES = int(os.environ.get("MAX_RETRIES", "4"))
BACKOFF = int(os.environ.get("RETRY_BACKOFF", "8"))
MARKER  = os.environ.get("PUBLISH_MARKER",
                         os.path.join(tempfile.gettempdir(), f"passit_reel_pub_{SHA[:12]}.done"))

ROOT   = os.path.dirname(os.path.abspath(__file__))
LATEST = os.path.join(ROOT, "reels", "latest")

vids = sorted(glob.glob(os.path.join(LATEST, "*.mp4")))
if not vids:
    sys.exit("Tidak ada .mp4 di reels/latest/")
video = vids[0]; fn = os.path.basename(video)

cap_path = os.path.join(LATEST, "caption.txt")
caption = open(cap_path, encoding="utf-8").read().strip() if os.path.exists(cap_path) else ""
if len(caption) > 2200:
    caption = caption[:2190].rstrip() + "…"

def jsdelivr(name):
    return f"https://cdn.jsdelivr.net/gh/{REPO}@{SHA}/reels/latest/{name}"
URL = jsdelivr(fn)

def g(p): return f"https://graph.facebook.com/{V}/{p}"

def meta_post(path, data, what):
    """POST ke Graph API dengan retry+backoff. Sukses = ada 'id' di respons."""
    last = None
    for a in range(1, RETRIES + 1):
        try:
            r = requests.post(g(path), data=data, timeout=180).json()
            if "id" in r:
                return r
            last = r
            print(f"  [{what}] percobaan {a}/{RETRIES} gagal: {r}")
        except Exception as e:
            last = {"exception": str(e)}
            print(f"  [{what}] percobaan {a}/{RETRIES} error: {e}")
        if a < RETRIES:
            time.sleep(BACKOFF * a)
    sys.exit(f"ERROR {what} setelah {RETRIES}x percobaan: {last}")

def ig_reel_container(url, cap):
    r = meta_post(f"{IG}/media", {
        "media_type": "REELS", "video_url": url, "caption": cap,
        "share_to_feed": "true", "access_token": TOKEN}, "reel container")
    return r["id"]

def ig_wait(cid):
    for i in range(40):
        try:
            r = requests.get(g(cid), params={
                "fields": "status_code,status", "access_token": TOKEN}, timeout=60).json()
        except Exception as e:
            print(f"  status[{i}] error jaringan: {e}"); time.sleep(6); continue
        sc = r.get("status_code")
        print(f"  status[{i}]: {sc}")
        if sc == "FINISHED": return
        if sc == "ERROR": sys.exit(f"Proses video ERROR: {r}")
        time.sleep(6)
    sys.exit("Timeout menunggu video FINISHED")

def ig_publish(cid):
    if os.path.exists(MARKER):
        print("  MARKER ada -> Reel sudah pernah dipublish di percobaan sebelumnya, skip (idempoten).")
        return "SKIPPED"
    r = meta_post(f"{IG}/media_publish", {
        "creation_id": cid, "access_token": TOKEN}, "publish")
    try:
        open(MARKER, "w").write(str(r.get("id", "done")))
    except Exception:
        pass
    return r["id"]

def fb_video(url, cap):
    if not PAGEID:
        print("Lewati FB: PAGE_ID kosong."); return
    for a in range(1, RETRIES + 1):
        try:
            r = requests.post(g(f"{PAGEID}/videos"), data={
                "file_url": url, "description": cap, "access_token": TOKEN}, timeout=180).json()
            if "id" in r:
                print("FB video OK:", r); return
            print(f"  [FB video] percobaan {a}/{RETRIES} gagal: {r}")
        except Exception as e:
            print(f"  [FB video] percobaan {a}/{RETRIES} error: {e}")
        if a < RETRIES:
            time.sleep(BACKOFF * a)
    print("  WARNING: FB video gagal setelah retry (IG Reel tetap terbit).")

# ---- alur utama ----
print(f"Repo {REPO} @ {SHA[:8]} | video {fn} | caption {len(caption)} char | FB={POSTFB}")
print("Video URL:", URL)
print("MARKER:", MARKER, "(ada)" if os.path.exists(MARKER) else "(belum ada)")

if os.path.exists(MARKER) and not FB_ONLY:
    print("Reel sudah dipublish di percobaan sebelumnya (MARKER ada). SELESAI tanpa aksi."); sys.exit(0)

print("Menghangatkan cache jsDelivr (biar Meta bisa fetch)...")
ok = False
for a in range(8):
    try:
        r = requests.get(URL, timeout=120)
        if r.status_code == 200 and int(r.headers.get("content-length", "0")) > 10000:
            print("  cache siap, bytes =", r.headers.get("content-length")); ok = True; break
        print("  belum siap:", r.status_code)
    except Exception as e:
        print("  ..", e)
    time.sleep(4)
if not ok:
    print("  WARNING: cache jsDelivr belum kebukti siap, lanjut coba tetap.")

if FB_ONLY:
    print("FB_ONLY: hanya FB Page..."); fb_video(URL, caption); print("SELESAI (FB only)"); sys.exit(0)

print("Bikin Reels container IG...")
cid = ig_reel_container(URL, caption)
print("Menunggu Meta memproses video...")
ig_wait(cid)
if DRY:
    print("[DRY_RUN] siap, tidak dipublish."); sys.exit(0)
print("Publish Reel ke Instagram...")
pid = ig_publish(cid)
print("IG Reel OK, media id:", pid)
if POSTFB:
    print("Cross-post video ke Facebook Page...")
    fb_video(URL, caption)
print("SELESAI")
