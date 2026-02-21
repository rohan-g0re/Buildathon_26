"""
Scoring logic — 4 metrics, aggregation after negotiation rounds.

See: docs/architecture/LLD_sandbox.md § 6
"""

import asyncio
import json
import logging
import re
import time
from agents.base import call_llm
from config.personas import DECISION_MAKER_PERSONAS, SCORING_PROMPT, SCORING_METRICS
from graph.sandbox.conversation import format_transcript
from models.state import SandboxState

log = logging.getLogger("sandbox.scoring")


async def score_move(state: SandboxState) -> dict:
    """
    After all rounds, each DM scores the move on 4 metrics.
    Three parallel scoring calls — all DMs receive the SAME shared
    conversation transcript and the original move content.
    """
    move = state["move_document"]
    move_id = move.get("move_id", "?")
    conversation = state["conversation"]

    log.info("[%s] Scoring START (3 DMs scoring in parallel after %d rounds)",
             move_id, state["current_round"])
    start = time.time()

    transcript = format_transcript(conversation)

    async def _score(dm_persona):
        prompt = SCORING_PROMPT.format(
            move_content=move["content"],
            transcript=transcript,
        )
        response = await call_llm(
            system_prompt=dm_persona["system_prompt"],
            user_prompt=prompt,
            max_tokens=512,
        )
        scores = _parse_scores(response, dm_persona["id"])
        return dm_persona["id"], scores

    tasks = [
        _score(DECISION_MAKER_PERSONAS[0]),
        _score(DECISION_MAKER_PERSONAS[1]),
        _score(DECISION_MAKER_PERSONAS[2]),
    ]
    results = await asyncio.gather(*tasks)

    scores_by_agent = {}
    total = 0
    for dm_id, score_dict in results:
        scores_by_agent[dm_id] = score_dict
        agent_total = sum(score_dict.get(m, 0) for m in SCORING_METRICS)
        log.info("[%s] %s scores: %s (subtotal=%d)", move_id, dm_id, score_dict, agent_total)
        total += agent_total

    elapsed = time.time() - start
    log.info("[%s] Scoring DONE: total=%d/120 (%.1fs)", move_id, total, elapsed)

    return {
        "scores": scores_by_agent,
        "total_score": total,
        "status_updates": [
            {"event": "sandbox_scored", "move": move["move_id"],
             "title": move.get("title", ""),
             "score": total, "breakdown": scores_by_agent}
        ],
    }


# ── JSON extraction helpers ──────────────────────────────────

def _strip_code_blocks(text: str) -> str:
    """Remove markdown code fences (```json ... ``` or ``` ... ```)."""
    # Match ```json\n...\n``` or ```\n...\n```
    pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _parse_scores(response: str, dm_id: str) -> dict:
    """
    Try multiple strategies to extract scores from the LLM response:
    1. Direct json.loads
    2. Strip markdown code blocks, then json.loads
    3. Regex fallback
    """
    # Strategy 1: direct parse
    try:
        return json.loads(response)
    except (json.JSONDecodeError, TypeError):
        pass

    # Strategy 2: strip code blocks then parse
    stripped = _strip_code_blocks(response)
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        pass

    # Strategy 3: regex fallback
    log.warning("[%s] Could not parse JSON scores, using regex fallback", dm_id)
    log.warning("[%s] Raw response (first 300 chars): %s", dm_id, response[:300])
    return _extract_scores_fallback(response)


def _extract_scores_fallback(response: str) -> dict:
    """Fallback: extract scores via regex if JSON parsing fails."""
    scores = {}
    for metric in SCORING_METRICS:
        # Try quoted key: "impact": 7
        match = re.search(rf'"{metric}"\s*:\s*(\d+)', response)
        if not match:
            # Try unquoted key: impact: 7
            match = re.search(rf'{metric}\s*:\s*(\d+)', response, re.IGNORECASE)
        scores[metric] = int(match.group(1)) if match else 5  # default neutral
    return scores
