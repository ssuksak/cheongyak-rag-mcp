"""Document parser for PDF and HWP files."""

import logging
from dataclasses import dataclass
from pathlib import Path

import fitz

logger = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    filename: str
    filepath: str
    file_type: str
    pages: list[dict]
    full_text: str
    metadata: dict
    page_count: int


MAX_FILE_SIZE = 50 * 1024 * 1024


def parse_pdf(filepath: str) -> ParsedDocument:
    file_size = Path(filepath).stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {file_size} bytes (max {MAX_FILE_SIZE})")

    doc = fitz.open(filepath)
    pages = []
    full_text_parts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if not text.strip():
            text = _extract_pdf_images_text(page)

        page_data = {
            "page_number": page_num + 1,
            "text": text,
            "char_count": len(text),
        }
        pages.append(page_data)
        if text.strip():
            full_text_parts.append(f"[페이지 {page_num + 1}]\n{text}")

    metadata = {
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", ""),
        "subject": doc.metadata.get("subject", ""),
        "creator": doc.metadata.get("creator", ""),
        "page_count": len(doc),
    }

    doc.close()

    return ParsedDocument(
        filename=Path(filepath).name,
        filepath=filepath,
        file_type="pdf",
        pages=pages,
        full_text="\n\n".join(full_text_parts),
        metadata=metadata,
        page_count=len(pages),
    )


def _extract_pdf_images_text(page) -> str:
    image_texts = []
    for img_info in page.get_images(full=True):
        xref = img_info[0]
        try:
            base_image = page.parent.extract_image(xref)
            if base_image and base_image.get("ext") == "png":
                image_texts.append(f"[이미지: xref={xref}]")
        except Exception:
            pass
    return "\n".join(image_texts)


def parse_hwp(filepath: str) -> ParsedDocument:
    try:
        import olefile

        ole = olefile.OleFileIO(filepath)
        text_parts = []

        if ole.exists("PrvText"):
            stream = ole.openstream("PrvText")
            preview = stream.read().decode("utf-16le", errors="ignore").strip()
            if preview:
                text_parts.append(preview)

        for entry in ole.listdir():
            entry_name = "/".join(entry)
            if entry_name.startswith("BodyText"):
                try:
                    s = ole.openstream(entry)
                    content = s.read().decode("utf-16le", errors="ignore").strip()
                    if content:
                        text_parts.append(content)
                except Exception:
                    pass

        ole.close()
        full_text = "\n\n".join(text_parts)

        return ParsedDocument(
            filename=Path(filepath).name,
            filepath=filepath,
            file_type="hwp",
            pages=[{"page_number": 1, "text": full_text, "char_count": len(full_text)}],
            full_text=full_text,
            metadata={"title": Path(filepath).stem, "page_count": 1},
            page_count=1,
        )
    except Exception as e:
        raise RuntimeError("HWP parsing failed. Install olefile: pip install olefile")


def parse_txt(filepath: str) -> ParsedDocument:
    file_size = Path(filepath).stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {file_size} bytes (max {MAX_FILE_SIZE})")

    for encoding in ["utf-8", "cp949", "euc-kr"]:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                text = f.read()
            break
        except UnicodeDecodeError:
            continue
    else:
        text = ""

    return ParsedDocument(
        filename=Path(filepath).name,
        filepath=filepath,
        file_type="txt",
        pages=[{"page_number": 1, "text": text, "char_count": len(text)}],
        full_text=text,
        metadata={"title": Path(filepath).stem, "page_count": 1},
        page_count=1,
    )


PARSERS = {
    ".pdf": parse_pdf,
    ".hwp": parse_hwp,
    ".txt": parse_txt,
    ".md": parse_txt,
    ".csv": parse_txt,
}


def parse_document(filepath: str) -> ParsedDocument:
    ext = Path(filepath).suffix.lower()
    parser = PARSERS.get(ext)

    if parser is None:
        raise ValueError(
            f"Unsupported file type: {ext}. Supported: {list(PARSERS.keys())}"
        )

    logger.info(f"Parsing {filepath} (type: {ext})")
    return parser(filepath)
