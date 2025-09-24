import io
from typing import List
import PyPDF2

def pdf2txt(file_stream: io.BytesIO) -> List[str]:
    reader = PyPDF2.PdfReader(file_stream)
    pages = []
    for p_idx, page in enumerate(reader.pages):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        pages.append({"page_num": p_idx + 1, "text": txt})
    return pages
