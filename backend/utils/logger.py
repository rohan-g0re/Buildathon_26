"""
Structured logging setup for the application.

Configures the root logger so ALL module loggers (pipeline, sse, llm,
layer_0, layer_1.*, layer_2.*, sandbox.*, output) inherit the same
format and handler.
"""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configures the root logger with a structured format.
    Call this ONCE at application startup (in main.py).
    """
    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S,%f",
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
