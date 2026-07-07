---
name: hermes-web-search
description: "Configure web search backends in Hermes Agent — DuckDuckGo, Exa, Firecrawl, Tavily, etc."
version: 1.0.0
author: agent
created_by: agent
metadata:
  hermes:
    tags: [hermes, web-search, configuration, exa, ddgs, firecrawl, tavily, mcp]
    related_skills: [hermes-agent, native-mcp]
---

# Hermes Web Search Configuration

Hermes Agent bundles 7 web search providers as plugins. Each supports **search** (query → result links), **extract** (URL → full content), or both. This skill covers how to set them up and switch between them.

## Available Providers

| Provider | Plugin name | Search | Extract | API Key | Free tier |
|----------|-------------|:------:|:-------:|---------|-----------|
| DuckDuckGo | `ddgs` | ✅ | ❌ | None | Unlimited |
| Exa | `exa` | ✅ | ✅ | `EXA_API_KEY` | 20,000/mo |
| Firecrawl | `firecrawl` | ✅ | ✅ | `FIRECRAWL_API_KEY` | ~500 pages/mo |
| Tavily | `tavily` | ✅ | ✅ | `TAVILY_API_KEY` | 1,000/mo |
| Parallel | `parallel` | ✅ | ✅ | `PARALLEL_API_KEY` | Paid |
| Brave Free | `brave-free` | ✅ | ❌ | None | ~2,000/mo |
| SearXNG | `searxng` | ✅ | ❌ | Self-hosted URL | Free |

## Quick Setup

### DuckDuckGo (free, no key needed)

```bash
# 1. Install the ddgs Python package
pip install ddgs

# 2. Set as search backend
hermes config set web.search_backend ddgs

# 3. Verify
python3 -c "from plugins.web.ddgs.provider import DDGSWebSearchProvider; p = DDGSWebSearchProvider(); print(p.is_available())"
```

DDG is **search-only** — cannot extract page content. Use with an extract backend (Firecrawl, Exa) if you need both.

### Exa (search + extract, API key needed)

```bash
# 1. Install the Exa SDK
pip install exa-py

# 2. Add API key to .env
echo 'export EXA_API_KEY="your-key-here"' >> ~/.hermes/.env

# 3. Set as both search and extract backend
hermes config set web.search_backend exa
hermes config set web.extract_backend exa

# 4. Verify
source ~/.hermes/.env && python3 -c "
from plugins.web.exa.provider import ExaWebSearchProvider
p = ExaWebSearchProvider()
print('Available:', p.is_available())
"
```

### Switching backends

```bash
# Change search backend only
hermes config set web.search_backend ddgs

# Change both search and extract to different providers
hermes config set web.search_backend exa
hermes config set web.extract_backend firecrawl

# Use the shared 'backend' field as fallback for both
hermes config set web.backend exa
```

The `web.backend` field is a shared fallback: if `search_backend` or `extract_backend` is empty, it falls back to `backend`.

## Architecture

Providers are plugins under `plugins/web/<name>/`. Each registers via `agent.web_search_registry`. Tool dispatch in `tools/web_tools.py` resolves providers at runtime:

- `web_search_tool()` → `get_active_search_provider()`
- `web_extract_tool()` → `get_active_extract_provider()`

The 7 providers are discovered on first tool call via `_ensure_web_plugins_loaded()`. Subagent and delegate runs trigger this automatically (fix for issue #27580).

## Pitfalls

### 1. `security.redact_secrets: true` masks keys in output
When this is enabled (default), API keys displayed in terminal output are masked. The .env file contains the real value — verify by checking key length/format rather than reading the raw value.

```python
# Safe verification pattern:
with open('/root/.hermes/.env') as f:
    for line in f:
        if 'EXA_API_KEY' in line:
            val = line.split('=')[1].strip().strip('"')
            assert len(val) == 36  # UUID format
            assert val.count('-') == 4
```

### 2. Search-only vs extract-only providers
Not all providers support both capabilities:
- **Search-only**: `ddgs`, `brave-free`, `searxng`
- **Both search + extract**: `exa`, `firecrawl`, `tavily`, `parallel`

If you try to use a search-only provider's extract, Hermes returns a typed "search-only" error rather than silently falling back.

### 3. Provider names are case-sensitive
Use lowercase in config: `ddgs`, `exa`, `firecrawl`. Uppercase (`DDGS`, `Exa`) won't match.

### 4. Package is separate from plugin
The plugin code ships with Hermes, but the underlying SDK is an optional dependency:
- `ddgs` → `pip install ddgs`
- `exa` → `pip install exa-py`
- `firecrawl` → `pip install firecrawl-py`
- `tavily` → `pip install tavily-python`

The plugin's `is_available()` checks importability, not API key status.

### 5. Changes take effect immediately
Unlike toolsets (which need `/reset`), web backend config is read fresh on every `web_search_tool` / `web_extract_tool` call. No restart needed.

## Verification

```bash
# Quick test without tool dispatch
python3 << 'EOF'
import json, os

# Pick a provider
provider_name = "exa"  # or ddgs, firecrawl, etc.
os.environ["EXA_API_KEY"] = "your-key"

from plugins.web.exa.provider import ExaWebSearchProvider
p = ExaWebSearchProvider()
print(f"Provider: {p.display_name}")
print(f"Available: {p.is_available()}")
print(f"Search: {p.supports_search()}, Extract: {p.supports_extract()}")

if p.is_available() and p.supports_search():
    result = p.search("test query", 2)
    data = result if isinstance(result, dict) else json.loads(result)
    print(f"Search works: {data.get('success')}")
EOF
```

## Exa MCP Alternative

Exa also provides an MCP server at `https://mcp.exa.ai/mcp` with OAuth-based auth (no API key needed). Configured under Hermes' native MCP client:

```yaml
# ~/.hermes/config.yaml
mcp:
  servers:
    exa:
      url: https://mcp.exa.ai/mcp
```

MCP tools available: `web_search_exa`, `web_fetch_exa`, `web_search_advanced_exa`. Enable advanced tools via `?tools=web_search_advanced_exa` in the URL.

Prefer the native plugin over MCP for Hermes — it integrates directly into the existing `web_search`/`web_extract` tool dispatch rather than exposing separate MCP tools.
