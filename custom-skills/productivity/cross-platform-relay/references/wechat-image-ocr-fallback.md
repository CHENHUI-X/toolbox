# Reading WeChat-Sent Images When the Vision Model Can't See Them

When 妈妈 (WeChat) sends an image and the active model/provider does not support
image content, `vision_analyze` fails (custom providers may return errors like
`unknown variant 'image_url', expected 'text'`). **Fall back to local tesseract
OCR for text-bearing images** — this is a retry/fallback pattern, not a dead end.

## One-time install

```bash
apt-get install -y tesseract-ocr tesseract-ocr-chi-sim   # chi_sim = Chinese
```

## Extract text

```bash
tesseract /abs/path/to/image.jpg /tmp/ocr_out -l chi_sim+eng 2>/dev/null
cat /tmp/ocr_out.txt
```

Use `-l chi_sim+eng` for Chinese+English documents (task requirements, forms,
schedules). Pass **absolute paths**. Avoid inline `python3 -c` pipelines into
tesseract — the lifecycle guard can reject commands containing embedded null
bytes; write preprocessing to a `.py` file first, then run it.

## Preprocessing for photos of printed text

Screenshots usually OCR fine as-is. For photos, upscale + boost contrast:

```python
from PIL import Image, ImageEnhance
img = Image.open('/abs/path/img.jpg').convert('L')       # grayscale
img = ImageEnhance.Contrast(img).enhance(2.0)            # boost contrast
img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)  # 2x upscale
img.save('/tmp/enhanced.png')
```

Then `tesseract /tmp/enhanced.png /tmp/out -l chi_sim+eng`.

## When OCR returns empty

**It's a photograph, not text** — no preprocessing extracts text that isn't
there. Stop looping OCR variants after 2-4 tries and tell the user plainly:
"牛牛的看图功能今天用不了（模型不支持图片），图片里有什么内容妈妈说一下？"
Ask them to describe the image (materials, tools, requirements). This happened
with a photo of 搭桥比赛工具 — OCR returned nothing, and asking the user was
the only path forward.

## Worked example (2026-07-20 session)

- 妈妈 sent two images via WeChat: a 任务要求 sheet and a 工具/材料 photo.
- `vision_analyze` failed 3× with `unknown variant 'image_url', expected 'text'`
  (deepseek-v4-flash via packyapi custom provider).
- Image 1 (任务要求, text) → OCR'd cleanly with `-l chi_sim+eng`.
- Image 2 (tools photo) → OCR empty → asked 妈妈 to describe the tools.
