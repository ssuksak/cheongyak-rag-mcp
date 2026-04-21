"""Text chunking module for Korean documents."""

import re
import uuid
from dataclasses import dataclass

from .config import get_config
from .parser import ParsedDocument


@dataclass
class Chunk:
    chunk_id: str
    document_filename: str
    document_filepath: str
    page_number: int | None
    chunk_index: int
    text: str
    char_count: int
    metadata: dict


def _split_korean_aware(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    paragraphs = re.split(r"\n\s*\n|\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 1 > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            overlap_text = current_chunk[-chunk_overlap:] if chunk_overlap > 0 else ""
            current_chunk = overlap_text + "\n" + para
        else:
            current_chunk = current_chunk + "\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def chunk_document(doc: ParsedDocument) -> list[Chunk]:
    config = get_config()
    chunks = []
    chunk_index = 0

    for page in doc.pages:
        text = page["text"]
        if not text.strip():
            continue

        page_chunks = _split_korean_aware(text, config.chunk_size, config.chunk_overlap)

        for text_chunk in page_chunks:
            chunk = Chunk(
                chunk_id=str(uuid.uuid4()),
                document_filename=doc.filename,
                document_filepath=doc.filepath,
                page_number=page["page_number"],
                chunk_index=chunk_index,
                text=text_chunk,
                char_count=len(text_chunk),
                metadata={
                    "filename": doc.filename,
                    "filepath": doc.filepath,
                    "file_type": doc.file_type,
                    "page_number": page["page_number"],
                    "chunk_index": chunk_index,
                    **doc.metadata,
                },
            )
            chunks.append(chunk)
            chunk_index += 1

    return chunks
