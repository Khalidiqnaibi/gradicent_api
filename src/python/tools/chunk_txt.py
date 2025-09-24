def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150):
    text = text.strip()
    if not text:
        return []
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        end = i + chunk_size
        chunk = text[i:end]
        chunks.append(chunk.strip())
        i += chunk_size - overlap
    return chunks
