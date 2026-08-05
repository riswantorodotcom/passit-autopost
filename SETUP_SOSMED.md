# Setup auto-post YouTube Shorts + TikTok (sekali saja)

Video harian (`reels/latest/reel.mp4`) yang sama dipakai untuk semua platform.
Workflow sudah terpasang: `post_youtube.yml` & `post_tiktok.yml`. Keduanya AMAN
menganggur (skip) sampai secrets di bawah diisi — Actions tetap hijau.

Tambahkan semua secret di: repo GitHub `passit-autopost` → Settings → Secrets and variables → Actions → New repository secret.

## A. YouTube Shorts
1. https://console.cloud.google.com → buat Project → aktifkan **YouTube Data API v3**.
2. OAuth consent screen: External, tambahkan akun Google channel PASSit sebagai Test user.
3. Credentials → Create → **OAuth client ID** → tipe **Desktop app**. Catat Client ID & Secret.
4. Di komputermu: `pip install google-auth-oauthlib`, lalu
   `YT_CLIENT_ID=... YT_CLIENT_SECRET=... python tools/get_yt_refresh_token.py`
   → login channel PASSit → setujui → salin **refresh token** yang tercetak.
5. Tambahkan secrets: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
6. PENTING: proyek API yang belum diaudit → video terkunci **private**. Untuk publik
   otomatis, ajukan **audit** YouTube API (sekali). Sementara belum, video ke-upload
   tapi private (bisa kamu publik-kan manual).

## B. TikTok (Direct Post / full-auto)
1. https://developers.tiktok.com → buat app → tambahkan produk **Content Posting API**,
   minta scope `video.publish` (+ `video.upload`).
2. Selesaikan login OAuth untuk akun TikTok PASSit → simpan **refresh token**
   (client_key/secret ada di dashboard app).
3. Tambahkan secrets: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN`.
4. Default aman: tanpa audit, post terkunci `SELF_ONLY` (privat). Setelah **audit
   Content Posting lolos** (~2–4 minggu), tambah secret `TIKTOK_PRIVACY=PUBLIC_TO_EVERYONE`
   agar tayang publik otomatis.

## Uji
Setelah secrets terisi, jalankan workflow via tab **Actions → Run workflow** (workflow_dispatch),
atau tunggu push reel harian berikutnya. Cek log job kalau ada error.
