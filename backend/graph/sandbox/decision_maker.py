"""
Decision maker agent logic — ALL DMs respond in parallel each round.

Each round, after the critic speaks, all 3 decision makers respond
simultaneously.  They see the full conversation through the critic's
latest message (and all prior rounds) but NOT each other's current-round
responses.

See: docs/architecture/LLD_sandbox.md § 5.2
"""

import asyncio
import logging
import time
from agents.base import call_llm
from config.personas import DECISION_MAKER_PERSONAS
from graph.sandbox.conversation import format_transcript
from models.state import SandboxState

log = logging.getLogger("sandbox.dm")


async def all_dms_respond(state: SandboxState) -> dict:
    """
    All 3 decision makers respond in parallel (asyncio.gather).
    Each DM sees the same conversation snapshot — up through the
    critic's latest message — so they do not influence each other
    within the same round.
    """
    move = state["move_document"]
    move_id = move.get("move_id", "?")
    round_num = state["current_round"]
    conversation = state["conversation"]
    transcript = format_transcript(conversation)

    log.info("[%s] All DMs round %d START", move_id, round_num)
    start = time.time()

    async def _single_dm(dm_persona):
        dm_id = dm_persona["id"]
        dm_name = dm_persona["name"]
        log.info("[%s]   %s (%s) — calling LLM", move_id, dm_id, dm_name)

        prompt = f"""
You are in a boardroom discussion about this business move for {state['ticker']}:

{move['content']}

Here is the full negotiation transcript so far:
{transcript}

Respond to the critic's latest points. You may also engage with arguments
made by other decision makers in prior rounds. Defend the move where you
believe it has merit, and concede where the critic makes valid points.

Be concise — respond in 2-3 paragraphs. Address the critic's strongest new point first.
"""

        response = await call_llm(
            system_prompt=dm_persona["system_prompt"],
            user_prompt=prompt,
            max_tokens=2048,
        )
        return dm_id, response

    results = await asyncio.gather(
        *[_single_dm(p) for p in DECISION_MAKER_PERSONAS]
    )

    elapsed = time.time() - start
    log.info("[%s] All DMs round %d DONE (%.1fs)", move_id, round_num, elapsed)

    new_entries = []
    status_messages = []
    for dm_id, response in results:
        log.info("[%s]   %s — %d chars", move_id, dm_id, len(response))
        entry = {"role": dm_id, "content": response, "round": round_num}
        new_entries.append(entry)
        status_messages.append(entry)

    return {
        "conversation": conversation + new_entries,
        "status_updates": [
            {"event": "sandbox_round", "move": move["move_id"],
             "round": round_num, "status": "dm_responded",
             "messages": status_messages}
        ],
    }
