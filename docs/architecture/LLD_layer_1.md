# Low-Level Design — Layer 1: Chunked Inference from Raw Data

## 1. Purpose

Layer 1 takes the raw data from Layer 0 and produces **two inference documents**:
- **F1** — Financial Inference Markdown
- **F2** — Trend Inference Markdown

Each agent processes its input in **~20-line chunks** rather than feeding the entire document at once. This prevents the LLM from being overloaded and produces focused, section-level analysis that is appended together.

---

## 2. Inputs & Outputs

| | Description |
|---|---|
| **Input** | `financial_data_raw: str` (Markdown from Layer 0) |
| **Input** | `news_data_raw: str` (Markdown from Layer 0) |
| **Output** | `f1_financial_inference: str` (F1 markdown document) |
| **Output** | `f2_trend_inference: str` (F2 markdown document) |

---

## 3. Agent Design

### 3.1 Two Agents, Parallel Execution

Layer 1 has exactly 2 agents:

| Agent | Input | Output | Persona |
|-------|-------|--------|---------|
| Financial Inference Agent | `financial_data_raw` | F1 markdown | Quantitative analyst — focuses on numbers, ratios, quarter-over-quarter changes |
| Trend Inference Agent | `news_data_raw` | F2 markdown | Market analyst — focuses on sentiment, narrative, competitive positioning |

Both agents run **in parallel** using LangGraph's `Send` API since their inputs and outputs are independent.

### 3.2 Chunked Processing Strategy

Each agent follows this pattern:

1. **Split** the raw markdown into chunks of ~20 lines using `split_into_chunks()`
2. **Process pairs** of chunks — for each pair (chunk i, chunk i+1), run both LLM calls in parallel via `asyncio.gather`
3. **Append** all chunk inferences in order, separated by `---`, to build the final document
4. **Prepend** a header (e.g., `# Financial Inference — {ticker}`)

For a 175-line financial document, this produces ~9 chunks, processed in ~5 sequential steps (pairs). Each LLM call generates 3-5 sentences of focused analysis.

### 3.3 System Prompts

The chunk-level personas instruct the LLM to produce **concise, section-specific** analysis (3-5 sentences per chunk) rather than a full document:

```python
# config/personas.py (Layer 1 chunk-level personas)

FINANCIAL_CHUNK_INFERENCE_PERSONA = """
You are a senior quantitative analyst at a top-tier investment bank.
You are given a SECTION of financial data for a publicly listed company
(not the full document — just one part of it).

Your job is to analyze THIS SPECIFIC SECTION and produce a concise inference.
Rules:
- Write 3-5 sentences of analysis for this section only.
- Cite exact numbers from the section.
- Describe what the data shows and what it implies.
- Do NOT make strategic recommendations — only describe and infer.
- Do NOT add headers, titles, or markdown structure — just write the
  inference paragraph directly.
- If the section is a table, focus on the most notable trends or outliers.
- If the section is prose (events, guidance), extract the key implications.

Be specific and concise. Every sentence must reference data from the section.
"""

TREND_CHUNK_INFERENCE_PERSONA = """
You are a senior market analyst specializing in competitive intelligence.
You are given a SECTION of news, sentiment, or competitive data for a
publicly listed company (not the full document — just one part of it).

Your job is to analyze THIS SPECIFIC SECTION and produce a concise inference.
Rules:
- Write 3-5 sentences of analysis for this section only.
- Reference specific sources, dates, or data points from the section.
- Describe what the section reveals about market sentiment, competitive
  dynamics, or investor perception.
- Do NOT make strategic recommendations — only describe and infer.
- Do NOT add headers, titles, or markdown structure — just write the
  inference paragraph directly.
- If the section contains Reddit comments, synthesize the crowd sentiment.
- If the section contains analyst ratings or prediction markets, extract
  the key signal.

Be specific and concise. Every sentence must reference data from the section.
"""
```

The original full-document personas (`FINANCIAL_INFERENCE_PERSONA`, `TREND_INFERENCE_PERSONA`) are preserved in `personas.py` for potential future use but are not used by the chunked agents.

---

## 4. Chunking Utility

```python
# agents/chunker.py

def split_into_chunks(text: str, chunk_size: int = 20) -> list[str]:
    """
    Splits text into chunks of approximately chunk_size lines.
    Skips empty chunks.
    """
    lines = text.strip().split("\n")
    chunks = []
    for i in range(0, len(lines), chunk_size):
        chunk = "\n".join(lines[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks
```

---

## 5. LangGraph Implementation

### 5.1 Fan-out using Send (unchanged)

```python
# graph/layer_1/node.py

from langgraph.types import Send

def dispatch_layer_1(state: dict) -> list[Send]:
    return [
        Send("financial_inference_agent", {
            "agent_type": "financial",
            "raw_data": state["financial_data_raw"],
            "ticker": state["company_ticker"],
        }),
        Send("trend_inference_agent", {
            "agent_type": "trend",
            "raw_data": state["news_data_raw"],
            "ticker": state["company_ticker"],
        }),
    ]
```

### 5.2 Agent Node Functions (chunked)

```python
# graph/layer_1/financial_inference.py

import asyncio
from agents.base import call_llm
from agents.chunker import split_into_chunks
from config.personas import FINANCIAL_CHUNK_INFERENCE_PERSONA


async def _infer_chunk(ticker: str, chunk: str, chunk_index: int) -> str:
    prompt = (
        f"Here is section {chunk_index + 1} of the financial data for {ticker}. "
        f"Provide a concise inference (3-5 sentences) analyzing what this "
        f"section reveals:\n\n{chunk}"
    )
    return await call_llm(
        system_prompt=FINANCIAL_CHUNK_INFERENCE_PERSONA,
        user_prompt=prompt,
        max_tokens=512,
    )


async def financial_inference_agent(state: dict) -> dict:
    ticker = state["ticker"]
    raw_data = state["raw_data"]

    chunks = split_into_chunks(raw_data, chunk_size=20)
    inferences: list[str] = []

    # Process chunks in pairs — 2 parallel LLM calls at a time
    for i in range(0, len(chunks), 2):
        tasks = [_infer_chunk(ticker, chunks[i], i)]
        if i + 1 < len(chunks):
            tasks.append(_infer_chunk(ticker, chunks[i + 1], i + 1))
        results = await asyncio.gather(*tasks)
        inferences.extend(results)

    # Assemble F1 document
    header = f"# Financial Inference — {ticker}\n"
    body = "\n\n---\n\n".join(inferences)
    f1 = f"{header}\n{body}\n"

    return {
        "f1_financial_inference": f1,
        "status_updates": [
            {"event": "agent_complete", "layer": 1,
             "agent_id": "financial_inference", "output": "F1"}
        ],
    }
```

The trend inference agent (`trend_inference.py`) follows the identical pattern using `TREND_CHUNK_INFERENCE_PERSONA`.

### 5.3 Reduce Node (unchanged)

```python
# graph/layer_1/reduce.py

def layer_1_reduce(state: dict) -> dict:
    return {
        "status_updates": [
            {"event": "layer_complete", "layer": 1, "status": "done",
             "artifacts": ["F1", "F2"]}
        ],
    }
```

---

## 6. LangGraph Wiring (in parent pipeline)

```python
# graph/pipeline.py (Layer 1 section)

from graph.layer_1.node import dispatch_layer_1
from graph.layer_1.financial_inference import financial_inference_agent
from graph.layer_1.trend_inference import trend_inference_agent
from graph.layer_1.reduce import layer_1_reduce

# Add nodes
builder.add_node("financial_inference_agent", financial_inference_agent)
builder.add_node("trend_inference_agent", trend_inference_agent)
builder.add_node("layer_1_reduce", layer_1_reduce)

# Layer 0 → fan-out to 2 parallel inference agents
builder.add_conditional_edges("layer_0_gather", dispatch_layer_1)

# Both agents → reduce
builder.add_edge("financial_inference_agent", "layer_1_reduce")
builder.add_edge("trend_inference_agent", "layer_1_reduce")

# Reduce → Layer 2
builder.add_edge("layer_1_reduce", "layer_2_dispatch")
```

---

## 7. Example: Processing a 175-line Financial Document

Given a 175-line `financial_data_raw.md`:

| Step | Chunks Processed | LLM Calls | Output |
|------|-----------------|-----------|--------|
| 1 | Chunk 0 (lines 1-20) + Chunk 1 (lines 21-40) | 2 parallel | 2 paragraphs |
| 2 | Chunk 2 (lines 41-60) + Chunk 3 (lines 61-80) | 2 parallel | 2 paragraphs |
| 3 | Chunk 4 (lines 81-100) + Chunk 5 (lines 101-120) | 2 parallel | 2 paragraphs |
| 4 | Chunk 6 (lines 121-140) + Chunk 7 (lines 141-160) | 2 parallel | 2 paragraphs |
| 5 | Chunk 8 (lines 161-175) | 1 call | 1 paragraph |
| **Total** | 9 chunks | 9 LLM calls (5 steps) | 9 paragraphs joined as F1 |

---

## 8. Error Handling

- If one chunk's LLM call fails, `asyncio.gather` propagates the exception. The `call_llm` function retries 3 times with exponential backoff before raising.
- If a chunk is mostly whitespace or separators, the LLM may return a minimal inference — this is acceptable and won't affect downstream layers.
- `max_tokens=512` per chunk call ensures fast, focused responses.

---

## 9. Testing Strategy

- **Unit test per agent:** Mock `call_llm`, verify the agent produces a markdown string with the correct header and multiple inference sections separated by `---`.
- **Integration test:** Run `test_layer_1.py` with real Layer 0 output, verify F1 and F2 are non-empty markdown files.
- **Chunk count test:** Verify `split_into_chunks` produces the expected number of chunks for a known input.
- **Parallel execution test:** Verify both agents run concurrently (timing check).
