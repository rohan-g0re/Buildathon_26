"""
Critic agent logic — one message per round on the shared conversation.

Each round the critic reads the full shared conversation and produces
a single response.  Round 1 is the opening critique; rounds 2+ respond
to whichever DM spoke last.

See: docs/architecture/LLD_sandbox.md § 5.1
"""

import logging
import time
from agents.base import call_llm
from config.personas import CRITIC_PERSONA
from graph.sandbox.conversation import format_transcript
from models.state import SandboxState

log = logging.getLogger("sandbox.critic")


async def critic_respond(state: SandboxState) -> dict:
    """
    Produce ONE critic message for this round.

    Round 1: opening critique of the move document.
    Round 2+: respond to the latest DM rebuttal in the shared conversation.
    """
    move = state["move_document"]
    move_id = move.get("move_id", "?")
    conversation = state["conversation"]
    round_num = state["current_round"] + 1

    log.info("[%s] Critic round %d START", move_id, round_num)
    start = time.time()

    if round_num == 1:
        # Opening critique — no prior conversation
        prompt = f"""
Here is a proposed business move for {state['ticker']}:

{move['content']}

Provide your initial counterpoints to this move. Challenge the reasoning,
question the evidence, and identify risks.

Be concise — focus on your top 3 counterpoints in 2-3 paragraphs.
"""
    else:
        # Respond to the latest DM rebuttal
        transcript = format_transcript(conversation)
        prompt = f"""
You are in round {round_num} of negotiation about this move for {state['ticker']}:

{move['content']}

The full conversation so far:
{transcript}

Respond to the latest decision maker's rebuttal. If they made good points,
acknowledge them. If they dodged your concerns, press harder. Raise new
counterpoints if you see additional weaknesses.

Be concise — respond in 2-3 focused paragraphs. Do not repeat prior points.
"""

    response = await call_llm(
        system_prompt=CRITIC_PERSONA,
        user_prompt=prompt,
        max_tokens=2048,
    )

    elapsed = time.time() - start
    log.info("[%s] Critic round %d DONE (%.1fs, %d chars)",
             move_id, round_num, elapsed, len(response))

    entry = {"role": "critic", "content": response, "round": round_num}

    return {
        "conversation": conversation + [entry],
        "current_round": round_num,
        "status_updates": [
            {"event": "sandbox_round", "move": move["move_id"],
             "round": round_num, "status": "critic_responded",
             "messages": [{"role": "critic", "content": response, "round": round_num}]}
        ],
    }
