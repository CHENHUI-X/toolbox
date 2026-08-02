# Delivering Files to WeChat Users (MEDIA: doesn't work)

## The Problem

On the WeChat (iLink bot) platform, sending `MEDIA:/path/to/file.csv` in a reply does NOT deliver a file attachment — the user receives the path rendered as an unclickable/link-like text string. Real user complaint:

> "打不开这个文件，怎么被当做链接发过来的？"

Same for image URLs: raw `https://...` image links don't render inline in the WeChat chat. The WeChat gateway only reliably renders **text**. So any file/image must be uploaded to a public host and the **direct download URL** sent as text.

## Working Fix (verified 2026-07 session)

**uguu.se** — free, no auth, returns a direct-download URL that works immediately (verified: `curl` of the returned URL yields the exact file bytes):

```python
import requests
with open('/root/.hermes/output/parker-services.csv', 'rb') as f:
    r = requests.post('https://uguu.se/upload.php',
                      files={'files[]': ('parker-services.csv', f)}, timeout=30)
    # r.json() -> {"success": true, "files": [{"url": "https://d.uguu.se/XXXX.csv", ...}]}
```

- Response JSON: `files[0].url` is the direct download link (host `d.uguu.se`).
- **Always verify the link before sending it** — `curl -sL <url> -o /tmp/check && file /tmp/check` should show the real MIME (e.g. `CSV Unicode text`), not `HTML document`.
- Link persists long enough for immediate download (it's a temp host — tell the user to download promptly).

## Services That Failed (don't waste time retrying)

| Service | Endpoint | Result |
|---|---|---|
| 0x0.st | `POST https://0x0.st` | 503 "uploads disabled … AI botnet spam" |
| catbox.moe | `POST https://catbox.moe/user/api.php` reqtype=fileupload | 412 Invalid uploader |
| transfer.sh | `PUT https://transfer.sh/<name>` | Network unreachable from GCP |
| file.io | `POST https://file.io` | API changed — returns Gatsby HTML SPA, no JSON link |
| tmpfiles.org | `POST https://tmpfiles.org/api/v1/upload` | Upload OK but returned URL serves an HTML viewer page, not raw bytes (both `/id/file` and `/dl/id/file`) |
| litterbox.catbox.moe | api.php reqtype=fileupload time=72h | Read timeout |

## User-Facing Flow

1. Try `MEDIA:` path → confirm user can't open it (or just skip and go straight to upload).
2. Upload via uguu.se, verify with `curl`/`file`, then send the direct link with a short explanation:
   > **下载链接：** https://d.uguu.se/XXXX.csv — 手机浏览器打开就能下载，用 WPS/Excel 打开
3. Optionally paste the file *content* as a Markdown table in the same message so the user gets the info even if they can't be bothered to download.

## Image Delivery (related)

Generated images (FAL etc.) also can't be shown inline on WeChat. Same pattern: download the image to disk, upload to a host that gives a direct link (or use the FAL media URL — the user can open it in a browser). Confirm with the user whether they can view it before assuming success.
