"""
Blaxel SDK wrapper — create, get, delete sandboxes.

All Blaxel interactions go through this file.
If you swap sandboxing providers, you change ONLY this file.

The blaxel import is LAZY — it only happens when functions are called,
not at module import time. This prevents ImportError when blaxel isn't
installed (e.g., local development with use_blaxel=False).

See: docs/architecture/LLD_sandbox.md § 9
"""

import logging
from config.settings import settings

logger = logging.getLogger(__name__)


def _get_sandbox_class():
    """Lazy import of blaxel.core.SandboxInstance."""
    try:
        from blaxel.core import SandboxInstance
        return SandboxInstance
    except ImportError:
        raise ImportError(
            "blaxel is not installed. Install it with `pip install blaxel` "
            "or set USE_BLAXEL=false in your .env to bypass."
        )


async def create_negotiation_sandbox(ticker: str, move_id: str):
    """
    Creates (or reuses) a Blaxel sandbox for a single policy negotiation.
    """
    SandboxInstance = _get_sandbox_class()
    sandbox_name = f"negotiate-{ticker.lower()}-{move_id}"

    sandbox = await SandboxInstance.create_if_not_exists({
        "name": sandbox_name,
        "image": "blaxel/base-image:latest",
        "memory": 2048,
        "labels": {
            "ticker": ticker,
            "move": move_id,
            "layer": "sandbox",
            "project": "ai-consulting-agency",
        },
        "region": settings.blaxel_region,
    })

    logger.info(f"Sandbox ready: {sandbox_name}")
    return sandbox


async def cleanup_sandbox(sandbox):
    """
    Cleans up a Blaxel sandbox after negotiation completes.
    """
    try:
        await sandbox.delete()
    except Exception as e:
        logger.warning(f"Failed to cleanup sandbox: {e}")


async def save_conversation_to_sandbox(
    sandbox,
    log_name: str,
    conversation: list[dict],
):
    """Saves a conversation log to the Blaxel sandbox filesystem."""
    import json
    content = json.dumps(conversation, indent=2)
    await sandbox.fs.write(f"/workspace/logs/{log_name}.json", content)


async def read_conversation_from_sandbox(
    sandbox,
    log_name: str,
) -> list[dict]:
    """Reads a conversation log from the Blaxel sandbox filesystem."""
    import json
    content = await sandbox.fs.read(f"/workspace/logs/{log_name}.json")
    return json.loads(content)
