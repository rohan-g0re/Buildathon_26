"""
Decision maker agent logic — ONE DM responds per round (round-robin).

Round 1 → D1, Round 2 → D2, Round 3 → D3, Round 4 → D1, ...

See: docs/architecture/LLD_sandbox.md § 5.2
"""

import logging
import time
from agents.base import call_llm
from config.personas import DECISION_MAKER_PERSONAS
from graph.sandbox.conversation import format_transcript
from models.state import SandboxState

log = logging.getLogger("sandbox.dm")

NUM_DMS = len(DECISION_MAKER_PERSONAS)


async def dm_respond(state: SandboxState) -> dict:
    """
    Exactly ONE decision maker responds per round, rotating round-robin.
    The DM reads the full shared conversation and the move document.
    """
    move = state["move_document"]
    move_id = move.get("move_id", "?")
    round_num = state["current_round"]
    conversation = state["conversation"]

    # Round-robin: round 1 → index 0 (D1), round 2 → index 1 (D2), etc.
    dm_index = (round_num - 1) % NUM_DMS
    dm_persona = DECISION_MAKER_PERSONAS[dm_index]
    dm_id = dm_persona["id"]
    dm_name = dm_persona["name"]

    log.info("[%s] DM round %d START — %s (%s)", move_id, round_num, dm_id, dm_name)
    start = time.time()

    transcript = format_transcript(conversation)
    prompt = f"""
You are defending this business move for {state['ticker']}:

{move['content']}

Here is the negotiation transcript so far:
{transcript}

Respond to the critic's latest points. Defend the move where you believe
it has merit, and concede where the critic makes valid points.

Be concise — respond in 2-3 paragraphs. Address the critic's strongest new point first.
"""

    response = await call_llm(
        system_prompt=dm_persona["system_prompt"],
        user_prompt=prompt,
        max_tokens=2048,
    )

    elapsed = time.time() - start
    log.info("[%s] DM round %d DONE — %s (%.1fs, %d chars)",
             move_id, round_num, dm_id, elapsed, len(response))

    entry = {"role": dm_id, "content": response, "round": round_num}

    return {
        "conversation": conversation + [entry],
        "status_updates": [
            {"event": "sandbox_round", "move": move["move_id"],
             "round": round_num, "status": "dm_responded",
             "messages": [{"role": dm_id, "content": response, "round": round_num}]}
        ],
    }
