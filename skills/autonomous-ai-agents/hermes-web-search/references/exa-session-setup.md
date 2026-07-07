# Exa Setup — Session 2026-06-24

## Context
User Parker Howard configured Hermes Agent web search. Started with DuckDuckGo (free), then switched to Exa for search + extract.

## Key decisions
- **Chose native Hermes plugin** over MCP server. The native `ExaWebSearchProvider` integrates into `web_search`/`web_extract` tools directly. MCP would expose separate `web_search_exa`/`web_fetch_exa` tools.
- **Exa API Key**: UUID format, `d104...0` — set as `export EXA_API_KEY="..."` in `.env`.
- **SDK**: `pip install exa-py` (v2.14.0 at time of setup).

## Config applied
```yaml
web:
  search_backend: exa
  extract_backend: exa
```

## Verification results
### Search test (量子计算 2026年最新进展)
✅ Returned 3 results with rich page-content highlights (not just meta descriptions):
- 中国电信光量子计算机"天衍-P2000" — from sina.com.cn
- 百万级原子光镊阵列芯片 — from 163.com
- 璇相科技百万光镊验证 — from 36kr.com

### Extract test (163.com article)
✅ Successfully pulled 7,194 characters of full page content including body text.

## Comparison with DuckDuckGo
| Aspect | DDGS | Exa |
|--------|:----:|:---:|
| Description source | Meta tags only | Page highlights (semantic) |
| Extract | ❌ | ✅ (full text) |
| Setup | pip install ddgs, set search_backend | pip install exa-py, API key, set both backends |
| Cost | Free | 20,000/mo free tier |

## Notes
- `security.redact_secrets: true` masks `EXA_API_KEY` in terminal output — use Python length verification instead of visual inspection.
- The Exa SDK's `.search()` with `contents={"highlights": True}` returns snippets from page body; `.get_contents(urls, text=True)` returns full raw text.
