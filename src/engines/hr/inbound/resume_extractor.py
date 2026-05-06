"""
Resume text extraction — supports PDF and DOCX.

Design: stateless functions, no class needed. The caller saves the file and
passes bytes + original filename. We detect file type from the extension
(not MIME sniffing) since recruiters always use proper extensions.
"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


def detect_file_type(file_bytes: bytes, filename: str) -> str:
    """Return 'pdf' or 'docx' based on filename extension. Raises ValueError for others."""
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return "pdf"
    if ext in ("docx", "doc"):
        return "docx"
    raise ValueError(f"Unsupported file type: .{ext}. Only PDF and DOCX are accepted.")


def extract_text_from_bytes(file_bytes: bytes, *, filename: str) -> str:
    """
    Extract plain text from a resume file.

    Returns extracted text (may be empty string for image-only PDFs).
    Raises ValueError for unsupported file types.
    """
    file_type = detect_file_type(file_bytes, filename)

    if file_type == "pdf":
        return _extract_pdf(file_bytes)
    return _extract_docx(file_bytes)


def _extract_pdf(file_bytes: bytes) -> str:
    import pdfplumber

    text_parts: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as exc:
        logger.warning("pdfplumber extraction failed: %s. Falling back to PyPDF2.", exc)
        text_parts = _extract_pdf_fallback(file_bytes)

    return "\n".join(text_parts).strip()


def _extract_pdf_fallback(file_bytes: bytes) -> list[str]:
    """PyPDF2 fallback when pdfplumber fails."""
    try:
        import PyPDF2

        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        return [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        logger.warning("PyPDF2 fallback also failed: %s. Returning empty string.", exc)
        return []


def _extract_docx(file_bytes: bytes) -> str:
    try:
        import docx2txt

        return docx2txt.process(io.BytesIO(file_bytes)).strip()
    except Exception as exc:
        logger.warning("docx2txt failed: %s. Trying python-docx.", exc)
        return _extract_docx_fallback(file_bytes)


def _extract_docx_fallback(file_bytes: bytes) -> str:
    try:
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(para.text for para in doc.paragraphs).strip()
    except Exception as exc:
        logger.warning("python-docx fallback failed: %s. Returning empty string.", exc)
        return ""
