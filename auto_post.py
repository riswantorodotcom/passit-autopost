#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_post.py (versi GitHub Actions) — posting carousel PASSit ke Instagram (+ Facebook Page).
Gambar di-host langsung dari repo ini via CDN jsDelivr (pakai commit SHA agar tidak kena cache basi).

Membaca dari environment (di-set oleh workflow dari GitHub Secrets):
  IG_USER_ID, PAGE_ACCESS_TOKEN, PAGE_ID (opsional), POST_TO_FACEBOOK, GRAPH_VERSION
  GITHUB_REPOSITORY, GITHUB_SHA (otomatis dari Actions)
  DRY_RUN (opsional: "true" untuk uji tanpa publish)

Slide + caption diambil dari folder latest/ :  slide_01.png ... slide_NN.png, caption.txt
"""
import os, sys, glob, json, time, requests

REPO   = os.environ["GITHUB_REPOSITORY"]
SHA    = os.environ.get("GITHUB_SHA", "main")
IG     = os.environ["IG_USER_ID"]
TOKEN  = os.environ["PAGE_ACCESS_TOKEN"]
PAGEID = os.environ.get("PAGE_ID", "")
POSTFB = os.environ.get("POST_TO_FACEBOOK", "true").lower() == "true"
V      = os.environ.get("GRAPH_VERSION", "v21.0")
DRY    = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")

ROOT   = os.path.dirname(os.path.abspath(__file__))
LATEST = os.path.join(ROOT, "latest")

slides = sorted(glob.glob(os.path.join(LATEST, "slide_*.png")))
if not slides:
    sys.exit("Tidak ada slide_*.png di folder latest/")
slides = slides[:10]

cap_path = os.path.join(LATEST, "caption.txt")
caption = ""
if os.path.exists(cap_path):
    caption = open(cap_path, encoding="utf-8").read().strip()
if len(caption) > 2200:
    caption = caption[:2190].rstrip() + "…"

def jsdelivr(fn):
    return f"https://cdn.jsdelivr.net/gh/{REPO}@{SHA}/latest/{fn}"

urls = [jsdelivr(os.path.basename(s)) for s in slides]
print(f"Repo {REPO} @ {SHA[:8]} | {len(urls)} slide | caption {len(caption)} char | FB={POSTFB}")
for u in urls:
    print("  ", u)

# Warm-up jsDelivr agar commit baru ter-cache sebelum Meta mengambilnya
print("Menghangatkan cache jsDelivr...")
for u in urls:
    for attempt in range(5):
        try:
            r = requests.get(u, timeout=60)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(3)

def g(path):
    return f"https://graph.facebook.com/{V}/{path}"

def ig_item(u):
    r = requests.post(g(f"{IG}/media"), data={
        "image_url": u, "is_carousel_item": "true", "access_token": TOKEN}, timeout=120).json()
    if "id" not in r:
        sys.exit(f"ERROR item container: {r}")
    return r["id"]

def ig_carousel(ids, cap):
    r = requests.post(g(f"{IG}/media"), data={
        "media_type": "CAROUSEL", "children": ",".join(ids),
        "caption": cap, "access_token": TOKEN}, timeout=120).json()
    if "id" not in r:
        sys.exit(f"ERROR carousel container: {r}")
    return r["id"]

def ig_publish(cid):
    r = requests.post(g(f"{IG}/media_publish"), data={
        "creation_id": cid, "access_token": TOKEN}, timeout=120).json()
    if "id" not in r:
        sys.exit(f"ERROR publish: {r}")
    return r["id"]

def fb_album(urls, cap):
    if not PAGEID:
        print("Lewati FB: PAGE_ID kosong.")
        return
    ids = []
    for u in urls:
        r = requests.post(g(f"{PAGEID}/photos"), data={
            "url": u, "published": "false", "access_token": TOKEN}, timeout=120).json()
        if "id" in r:
            ids.append(r["id"])
        else:
            print(f"FB foto gagal: {r}")
    if not ids:
        return
    att = [{"media_fbid": i} for i in ids]
    r = requests.post(g(f"{PAGEID}/feed"), data={
        "message": cap, "attached_media": json.dumps(att), "access_token": TOKEN}, timeout=120).json()
    print("FB feed:", r)

print("Bikin item container Instagram...")
child = []
for u in urls:
    child.append(ig_item(u))
    time.sleep(1)

print("Bikin carousel container...")
carousel = ig_carousel(child, caption)
time.sleep(3)

if DRY:
    print("[DRY_RUN] Siap, tidak dipublish.")
    sys.exit(0)

print("Publish ke Instagram...")
pid = ig_publish(carousel)
print("IG OK, media id:", pid)

if POSTFB:
    print("Cross-post ke Facebook Page...")
    fb_album(urls, caption)

print("SELESAI")
