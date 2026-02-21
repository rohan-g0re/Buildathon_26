"""
Analyst agent logic — reused with different personas.
Each invocation produces 3 moves (low, medium, high risk).

See: docs/architecture/LLD_layer_2.md § 4.2
"""

import logging
import re
from agents.base import call_llm
from config.personas import MOVE_GENERATION_PROMPT

log = logging.getLogger("layer_2.analyst")


async def analyst_agent(state: dict) -> dict:
    """
    Single analyst agent. Called 5 times in parallel via Send.
    Each invocation has a different persona.
    Produces 3 moves (low, medium, high risk).
    """
    persona = state["persona"]
    ticker = state["ticker"]

    log.info("Analyst '%s' (%s) START for %s", persona["name"], persona["id"], ticker)

    prompt = MOVE_GENERATION_PROMPT.format(
        ticker=ticker,
        f1=state["f1"],
        f2=state["f2"],
    )

    raw_response = await call_llm(
        system_prompt=persona["system_prompt"],
        user_prompt=prompt,
    )

    moves = _parse_three_moves(raw_response, persona, ticker)
    move_ids = [m["move_id"] for m in moves]
    log.info("Analyst '%s' DONE — %d moves: %s", persona["name"], len(moves), move_ids)

    return {
        "move_suggestions": moves,
        "status_updates": [
            {"event": "agent_complete", "layer": 2,
             "agent_id": persona["id"], "persona": persona["name"],
             "move_count": len(moves)}
        ],
    }


def _parse_three_moves(response: str, persona: dict, ticker: str) -> list[dict]:
    """Parses the LLM response into 3 structured move dicts."""
    risk_levels = ["low", "medium", "high"]
    moves = []

    sections = _split_into_sections(response)

    for i, risk in enumerate(risk_levels):
        section = _find_section_for_risk(sections, risk)
        if section is None and i < len(sections):
            section = sections[i]
        if section is None:
            section = ""
        move_id = f"m{_get_global_move_index(persona['id'], i)}"
        moves.append({
            "move_id": move_id,
            "agent_id": persona["id"],
            "persona": persona["name"],
            "risk_level": risk,
            "title": _extract_title(section),
            "content": section.strip(),
            "ticker": ticker,
        })

    return moves


def _find_section_for_risk(sections: list[str], risk: str) -> str | None:
    """Finds the section matching a given risk level by its header."""
    pattern = re.compile(rf'{risk}[\-\s]*risk\s+move', re.IGNORECASE)
    for section in sections:
        if pattern.search(section):
            return section
    return None


def _get_global_move_index(agent_id: str, local_index: int) -> int:
    """Maps (agent_id, local_index) → global move number (1-15)."""
    agent_num = int(agent_id.split("_")[1])
    return (agent_num - 1) * 3 + local_index + 1


def _split_into_sections(response: str) -> list[str]:
    """Splits LLM response into sections by --- delimiters, skipping any preamble."""
    sections = re.split(r'\n---\n', response)
    return [s for s in sections if s.strip() and re.search(r'Move:\s*.+', s)]


def _extract_title(section: str) -> str:
    """Extracts the title from a move section header."""
    match = re.search(r'Move:\s*(.+)', section)
    return match.group(1).strip() if match else "Untitled Move"
