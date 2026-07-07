---
name: web-search-routing
description: "Routing strategy for web search: DuckDuckGo for quick searches, Exa for deep content extraction"
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [web, search, exa, ddgs, duckduckgo, routing]
---

# Web Search Routing Strategy

This skill defines when to use DuckDuckGo (DDGS) vs Exa for web searches.

## Configuration (already set)

```yaml
web:
  search_backend: ddgs    # → web_search 走 DuckDuckGo (免费无限)
  extract_backend: exa    # → web_extract 走 Exa (20,000次/月配额)
```

## Routing Rules

### ✅ Use `web_search` (DuckDuckGo) when:
- Quick fact lookup (天气、时间、定义、人名等)
- Finding relevant URLs on a topic
- News headlines / recent events summary
- General knowledge that just needs titles + brief descriptions
- Anything where URLs are the goal, not full content
- **Cost: free, unlimited**

### 🔥 Use `web_extract` (Exa) when:
- User needs **full page content** or article text
- Need to extract specific details from a particular URL
- Content summarization / analysis from a known page
- Research deep-dive from specific sources
- Need structured data from a webpage
- **Cost: consumes Exa quota (20k/month)**

### 🔄 Combined workflow (search → extract):
```
1. web_search(query)      → get relevant URLs (DDG, free)
2. web_extract(urls)      → pull full content (Exa, targeted)
```

This two-step approach minimizes Exa quota usage — you only extract from URLs that actually look relevant, rather than burning Exa searches on every query.

## Notes
- DuckDuckGo is **search-only** (no extract capability) — it's the right tool for cheap discovery
- Exa supports **both search and extract**, but use it only for `web_extract` to conserve monthly quota
- Exa quota resets monthly — monitor via https://exa.ai/dashboard
- If Exa quota runs out, you can temporarily set `web.extract_backend: ""` and use `browser_navigate` instead for page reading

## Programmatic Usage

When the `web_search`/`web_extract` agent tools aren't directly available, use the search providers via Python imports. See `references/provider-import-paths.md` for:

- **DDGS (DuckDuckGo)** — `from ddgs import DDGS` (free, search only)
- **Exa via Hermes plugin** — `from plugins.web.exa.provider import ExaWebSearchProvider` (paid, search + extract)
- **Exa via raw SDK** — `from exa_py import Exa` (backup path)
- Credential sourcing from `.env`
- Common pitfalls (plugin discovery, secret redaction, rate limits)

## Fallback Techniques

When standard search/extract tools fail (site unreachable, SPA/dynamic content, curl can't parse), try these alternatives before giving up:

### 1. Mirror / Aggregator Sites
The target site might work at a different domain. Search for mirrors first before declaring the content unreachable.

### 2. JSON-LD Structured Data Extraction
Many modern sites embed schema.org data in `<script type="application/ld+json">` tags for SEO. This data is **pure JSON** embedded in the HTML — curl can extract it even when the visible page requires JavaScript to render.

**Workflow:**
```
curl -sL URL | grep -o 'application/ld+json' ... → parse with json.loads()
```

**Best for:** video catalogs, product listings, article archives, recipe collections, event schedules — any site that wants Google to index its content.

See `references/json-ld-extraction.md` for the full technique, code patterns, and a real worked example.
