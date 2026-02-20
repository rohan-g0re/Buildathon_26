"""
Text chunking utility for splitting markdown documents into manageable pieces.

Used by Layer 1 inference agents to process raw data in ~20-line chunks
rather than feeding the entire document to the LLM at once.

See: docs/architecture/LLD_layer_1.md
"""


def split_into_chunks(text: str, chunk_size: int = 20) -> list[str]:
    """
    Splits text into chunks of approximately chunk_size lines.

    Args:
        text: The full markdown text to split.
        chunk_size: Target number of lines per chunk (default 20).

    Returns:
        A list of strings, each containing ~chunk_size lines of the original text.
    """
    lines = text.strip().split("\n")
    chunks = []
    for i in range(0, len(lines), chunk_size):
        chunk = "\n".join(lines[i:i + chunk_size])
        if chunk.strip():  # skip empty chunks
            chunks.append(chunk)
    return chunks
