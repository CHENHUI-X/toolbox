# JSON-LD Structured Data Extraction

A fallback technique for extracting structured data from web pages when standard tools (curl, browser) can't render the dynamic content.

## When to Use This

- The target site is an SPA (Angular, React, Vue) — content loads via JS, curl returns empty shells
- Browser tools are unavailable or the site blocks automated browsers
- You need bulk structured data (titles, URLs, view counts, dates, authors)
- The site wants Google to index it — almost guarantee they embed schema.org JSON-LD

## How It Works

Most modern sites embed `<script type="application/ld+json">` blocks in the HTML for SEO. This is pure JSON embedded in the page source — it survives curl, `wget`, and any HTTP client that doesn't execute JavaScript.

## Code Pattern

```python
import json, re

# Step 1: Fetch the page
# curl -sL "https://example.com" -o page.html

# Step 2: Read and extract JSON-LD
with open('page.html', 'r') as f:
    html = f.read()

ld = re.search(
    r'<script type="application/ld\+json">(.*?)</script>',
    html, re.DOTALL
)
if ld:
    data = json.loads(ld.group(1))
    # Now navigate the schema.org structure
    # Common shapes:
    items = data.get('mainEntity', {}).get('itemListElement', [])
    for entry in items:
        item = entry.get('item', {})
        name = item.get('name', '')
        url = item.get('url', '')
        views = item.get('interactionStatistic', [{}])[0].get('userInteractionCount', '')
        duration = item.get('duration', '')
        author = item.get('author', {}).get('name', '')
```

## Schema.org Shapes Encountered

| Shape | Pattern | Usage |
|-------|---------|-------|
| `CollectionPage` | `data.mainEntity.ItemList.ItemListElement[].item` | Ranked lists (videos, products) |
| `VideoObject` | Direct `VideoObject` in `@graph` | Individual video pages |
| `Product` | `data.mainEntity` | Product pages with offers |
| `Article` / `NewsArticle` | `data.mainEntity` | News sites |
| `BreadcrumbList` | `data.mainEntity.itemListElement` | Navigation context |

## Where JSON-LD Lives

Check these locations in the HTML (in order of likelihood):
1. `<script type="application/ld+json">` — most common
2. `<script type="application/ld+json" class="yoast-schema-graph">` — WordPress/Yoast
3. Multiple blocks — some sites have separate blocks for different entity types (breadcrumbs, videos, FAQ)

## Real Worked Example

**Goal:** Get Top 10 hottest videos from 91spx.com with titles, view counts, and direct links.

**Challenge:** The site is an Angular SPA. `curl` returned 266KB of HTML but the visible video grid was rendered by JavaScript. No video titles visible in rendered text.

**Solution:** Found JSON-LD in the page source with a complete `CollectionPage` schema including `ItemList` with 49,249 items, each containing `VideoObject` with name, description, url, duration, uploadDate, author, and `interactionStatistic` (view count).

**Extracted data (Top 3):**

| # | Title | Views |
|---|-------|-------|
| 1 | 高颜值老A8被精神小伙3000元征服… | 146,316 |
| 2 | 反差婊深喉撸管必看高能合集… | 251,994 |
| 3 | 女神高潮盛宴合集… | 148,273 |

**One-liner version:**
```bash
curl -sL 'https://example.com/videos/hot/' | \
  python3 -c "
import json, sys, re
html = sys.stdin.read()
ld = re.search(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL)
if ld:
    data = json.loads(ld.group(1))
    for e in data['mainEntity']['itemListElement'][:5]:
        i = e['item']
        print(f\"{i['name']} — {i['interactionStatistic'][0]['userInteractionCount']} views — {i['url']}\")
"
```

## Pitfalls

- **Single-page vs list page:** JSON-LD on an SPA page typically has the schema for ALL items even if the UI only shows page 1 — you get the full dataset in one fetch
- **Rate limiting:** Some sites serve different JSON-LD to bots vs browsers. Use a realistic User-Agent
- **Encoding:** Always open files with `encoding='utf-8', errors='ignore'`
- **Nested structures:** `interactionStatistic` is an array — always index `[0]` or loop
- **Duration format:** Schema.org uses ISO 8601 (`PT30M14S`). Parse with `isodate` or regex if needed
