"""
Conversation log management — append, format, read for shared conversation.

See: docs/architecture/LLD_sandbox.md § 10
"""

from models.state import ConversationEntry


def append_to_log(
    current_log: list[ConversationEntry],
    role: str,
    content: str,
    round_num: int,
) -> list[ConversationEntry]:
    """
    Appends a new entry to a conversation log.
    Returns a NEW list (immutable state update for LangGraph).
    """
    return current_log + [{
        "role": role,
        "content": content,
        "round": round_num,
    }]


def format_transcript(conversation: list[ConversationEntry]) -> str:
    """
    Formats a conversation log as a human-readable transcript.
    This is what gets passed to the LLM on each call.
    """
    lines = []
    for entry in conversation:
        if entry["role"] == "critic":
            role_label = "CRITIC"
        else:
            role_label = f"DECISION MAKER ({entry['role']})"

        lines.append(
            f"**[Round {entry['round']}] {role_label}:**\n"
            f"{entry['content']}"
        )
    return "\n\n---\n\n".join(lines)


def get_latest_message(conversation: list[ConversationEntry]) -> str:
    """Returns the content of the most recent message in the log."""
    if not conversation:
        return ""
    return conversation[-1]["content"]
