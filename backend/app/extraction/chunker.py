def chunk_text(text: str, max_tokens: int = 1200) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) > max_tokens:
            if current:
                chunks.append(current)
            current = ""
        current += line + "\n"
    if current:
        chunks.append(current)
    return chunks
