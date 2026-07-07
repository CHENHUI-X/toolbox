# Web Search Provider Import Paths

When the standard `web_search`/`web_extract` agent tools aren't directly available, use these Python import paths to use the search providers programmatically via `terminal()` or `execute_code()`.

## DuckDuckGo (ddgs) — Free, Search Only

```python
from ddgs import DDGS

results = DDGS().text("your query", max_results=5)
for r in results:
    print(r.get("title", ""))
    print(r.get("href", ""))
    print(r.get("body", "")[:150])
```

**Returns:** List of dicts with keys: `title`, `href`, `body`, `position`
**Pitfall:** The `ddgs` package is NOT Hermes-internal — install it separately: `pip install ddgs`
**Capability:** Search only (no content extraction)

## Exa — Paid (20k/mo free), Search + Extract

### Via the Hermes plugin (preferred — respects config):

```python
from plugins.web.exa.provider import ExaWebSearchProvider
p = ExaWebSearchProvider()
```

**Requires:** `EXA_API_KEY` env var set, and `exa-py` package installed (`pip install exa-py`)
**Automatic credential resolution:** reads from `.env` / environment

#### Search
```python
result = p.search("your query", limit=5)
# Returns dict: {"success": True, "data": {"web": [{"title", "url", "description", "position"}, ...]}}
```

The `description` field contains **page content highlights** (not just meta descriptions) — Exa indexes full page text.

#### Extract
```python
results = p.extract(["https://example.com/article"])
# Returns list of dicts: [{"url", "title", "content", "raw_content", "metadata"}]
```

Content is typically 5,000-20,000 chars of full page text.

### Via the raw Exa SDK (backup):

```python
from exa_py import Exa
import os

client = Exa(api_key=os.environ["EXA_API_KEY"])
response = client.search("query", num_results=5)
```

## Which One to Use

| Situation | Choice | Why |
|-----------|--------|-----|
| Quick search, no API key | `ddgs` | Free, unlimited, no auth |
| Need full page content | `ExaWebSearchProvider` | 20k/mo quota, returns real text |
| Search and then extract from results | `ddgs` search + `ExaWebSearchProvider` extract | Save Exa quota for extraction only |
| Need to source `.env` first | Prefix with `source ~/.hermes/.env &&` | Environment doesn't auto-inherit in `terminal()` |

## Sourcing Credentials

The `.env` file is NOT automatically loaded in `terminal()` or `execute_code()` unless you explicitly source it:

```bash
source ~/.hermes/.env && python3 -c "..."
```

Or set the env var inline:

```python
import os
os.environ["EXA_API_KEY"] = "your-key-here"
```

## Common Pitfalls

1. **`module 'plugins' has no attribute 'web'`** — Only happens when the Hermes plugin discovery hasn't run. For one-off scripts, use the raw SDK (`from exa_py import Exa`).
2. **Secret redaction** — If `security.redact_secrets: true`, API keys are masked in tool output. The actual file content is correct; output display is filtered.
3. **JSON-LD extraction** — For SPA sites where curl returns minimal HTML, try JSON-LD extraction first (see `references/json-ld-extraction.md`).
4. **DDGS rate limits** — DDGS is a scraper, not an API. It may get rate-limited on heavy use (50+ searches/minute). Add `time.sleep(1)` between calls for bulk work.
