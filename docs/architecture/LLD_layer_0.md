# Low-Level Design — Layer 0: Synthetic Data Generation

## 1. Purpose

Layer 0 generates **synthetic financial and news data** for the target company using an LLM agent. It has **one LangGraph node** that makes **two parallel LLM calls** — one for financial data, one for news/sentiment data. Both outputs are Markdown strings that feed Layer 1.

This is a prototype simplification. In production, Layer 0 would call real APIs (Yahoo Finance, NewsAPI, Reddit, etc.). For now, the LLM synthesizes realistic data following a fixed template.

---

## 2. Inputs & Outputs

| | Description |
|---|---|
| **Input** | `company_ticker: str` (e.g., `"AAPL"`, `"TSLA"`) |
| **Output 1** | `financial_data_raw: str` — synthetic financial data (~2 pages, Markdown) |
| **Output 2** | `news_data_raw: str` — synthetic news + sentiment data (~2 pages, Markdown) |

---

## 3. Agent Design

### 3.1 Single Node, Two Parallel LLM Calls

Layer 0 has exactly 1 LangGraph node (`layer_0_synthesize`) that internally makes 2 parallel calls via `asyncio.gather`:

| Call | System Prompt | Output | Template |
|------|--------------|--------|----------|
| Financial Data | `DATA_SYNTHESIZER_FINANCIAL_PERSONA` | `financial_data_raw` (Markdown) | `FINANCIAL_DATA_TEMPLATE` |
| News Data | `DATA_SYNTHESIZER_NEWS_PERSONA` | `news_data_raw` (Markdown) | `NEWS_DATA_TEMPLATE` |

Both calls use **Claude Haiku** (`claude-haiku-4-5`) via the Anthropic Python SDK.

### 3.2 System Prompts

```python
# config/personas.py (Layer 0 personas)

DATA_SYNTHESIZER_FINANCIAL_PERSONA = """
You are a financial data provider at a top-tier market intelligence firm.
Your job is to produce a comprehensive, realistic financial data package
for a publicly listed company in Markdown format.

Rules:
- Generate synthetic but internally consistent data — numbers must tell
  a coherent story (revenue trends, margin movements, balance sheet items
  should all fit together logically).
- Include conflicting signals — some metrics should look strong while
  others raise concerns. Real companies are never unambiguously good or bad.
- Follow the EXACT section structure and table formats from the example
  provided in the user prompt. Do not add or remove sections.
- Keep the output to approximately 2 pages of Markdown (tables + prose).
- Include specific numbers, dates, names, and events — never be vague.
- If the company is real, base the narrative loosely on its actual sector
  and business model, but all specific numbers should be synthetic.
- If the ticker is not recognized, invent a plausible company with a
  clear business model and sector.

Output ONLY the Markdown document. No preamble, no commentary, no wrapping.
"""

DATA_SYNTHESIZER_NEWS_PERSONA = """
You are a market intelligence analyst at a premier research firm.
Your job is to produce a comprehensive, realistic news and sentiment
brief for a publicly listed company in Markdown format.

Rules:
- Generate synthetic but realistic news articles, Reddit discussions,
  prediction market signals, competitor activity, and analyst ratings.
- Include mixed sentiment — some bullish, some bearish, some neutral.
  Real market discourse is never one-sided.
- Follow the EXACT section structure and formatting from the example
  provided in the user prompt. Do not add or remove sections.
- Keep the output to approximately 2 pages of Markdown.
- Include specific source names, dates, sentiment tags, upvote counts,
  probabilities, and analyst targets — never be vague.
- Reddit comments should feel authentic — mix of informed analysis,
  speculation, and casual language.
- If the company is real, base the narrative loosely on its actual sector
  and competitive landscape, but all specific content should be synthetic.
- If the ticker is not recognized, invent plausible competitors and
  market dynamics.

Output ONLY the Markdown document. No preamble, no commentary, no wrapping.
"""
```

---

## 4. Template Injection

Each LLM call includes a **few-shot example** in the user prompt. The examples are extracted from `EXAMPLE_DATA_FORMAT.md` and stored as Python string constants in `graph/layer_0/templates.py`:

- `FINANCIAL_DATA_TEMPLATE` — a complete financial data package for a fictional company (NovaTech Inc., NVTK), including quarterly revenue, segment breakdowns, income statement, balance sheet, cash flow, stock prices, ratios, business metrics, management guidance, and corporate events.
- `NEWS_DATA_TEMPLATE` — a complete news/sentiment brief for the same company, including news articles, Reddit threads, Polymarket signals, competitor activity, and analyst ratings.

The user prompt instructs the LLM to follow the **exact same structure** but generate new data for the target ticker.

---

## 5. LangGraph Node Definition

```python
# graph/layer_0/node.py

import asyncio
from models.state import PipelineState
from agents.base import call_llm
from config.personas import (
    DATA_SYNTHESIZER_FINANCIAL_PERSONA,
    DATA_SYNTHESIZER_NEWS_PERSONA,
)
from graph.layer_0.templates import FINANCIAL_DATA_TEMPLATE, NEWS_DATA_TEMPLATE


async def layer_0_synthesize(state: PipelineState) -> dict:
    ticker = state["company_ticker"]

    financial_prompt = (
        f"Generate a synthetic financial data package for the company "
        f"with ticker {ticker}.\n\n"
        f"Here is an example for a different company (NovaTech Inc., NVTK). "
        f"Follow the EXACT same structure, section headers, and table formats, "
        f"but generate completely new data for {ticker}:\n\n"
        f"{FINANCIAL_DATA_TEMPLATE}"
    )

    news_prompt = (
        f"Generate a synthetic news and sentiment brief for the company "
        f"with ticker {ticker}.\n\n"
        f"Here is an example for a different company (NovaTech Inc., NVTK). "
        f"Follow the EXACT same structure, section headers, and formatting, "
        f"but generate completely new data for {ticker}:\n\n"
        f"{NEWS_DATA_TEMPLATE}"
    )

    financial_raw, news_raw = await asyncio.gather(
        call_llm(
            system_prompt=DATA_SYNTHESIZER_FINANCIAL_PERSONA,
            user_prompt=financial_prompt,
        ),
        call_llm(
            system_prompt=DATA_SYNTHESIZER_NEWS_PERSONA,
            user_prompt=news_prompt,
        ),
    )

    return {
        "financial_data_raw": financial_raw,
        "news_data_raw": news_raw,
        "status_updates": [
            {"event": "layer_complete", "layer": 0, "status": "done"}
        ],
    }
```

---

## 6. LLM Call Path

All LLM calls go through the Anthropic Python SDK:

```python
# agents/base.py → agents/llm.py

from anthropic import AsyncAnthropic

# Singleton client
client = AsyncAnthropic(api_key=settings.anthropic_api_key)

# Each call
message = await client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=4096,
    temperature=0.7,
    system=system_prompt,          # top-level param, not a message
    messages=[{"role": "user", "content": user_prompt}],
)
response_text = message.content[0].text
```

Key points:
- `system` is a top-level parameter in the Anthropic API (not a message role)
- `max_tokens` is required — defaults to 4096 for data synthesis
- Retries with exponential backoff (1s, 2s, 4s) on failure

---

## 7. File Structure

```
backend/graph/layer_0/
├── node.py                   # layer_0_synthesize — the LangGraph node
├── templates.py              # FINANCIAL_DATA_TEMPLATE, NEWS_DATA_TEMPLATE
├── EXAMPLE_DATA_FORMAT.md    # Documentation / reference for template format
└── scrapers/
    └── .gitkeep              # Reserved for future real-API scrapers
```

---

## 8. Error Handling

- If one LLM call fails (API error, rate limit), `asyncio.gather` propagates the exception. The `call_llm` function retries 3 times with exponential backoff before raising.
- If the LLM generates malformed output (wrong structure, missing sections), Layer 1 agents can still process it since they treat the data as opaque text. Quality degradation is graceful.
- A future improvement could validate the LLM output against expected section headers before passing it downstream.

---

## 9. Testing Strategy

- **Unit test:** Mock `call_llm`, verify `layer_0_synthesize` returns a dict with `financial_data_raw`, `news_data_raw`, and `status_updates`.
- **Integration test:** Run with a real API key and verify both outputs are non-empty Markdown strings containing expected section headers.
- **Parallel execution test:** Verify both LLM calls run concurrently (timing check — should be ~1x, not ~2x, the time of a single call).
