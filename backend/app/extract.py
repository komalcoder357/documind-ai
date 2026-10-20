import io, os, zipfile
import pymupdf, docx

class ExtractError(Exception):
    def __init__(self, msg, status=422): super().__init__(msg); self.status = status

ALLOWED = {".pdf": "pdf", ".docx": "docx", ".txt": "txt"}

def decode_text(raw: bytes) -> str:
    if b"\x00" in raw[:4096] and not raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise ExtractError("File content is not plain text.", 415)
    for enc in ("utf-8-sig", "utf-16"):
        try: return raw.decode(enc)
        except UnicodeDecodeError: pass
    raise ExtractError("Unsupported text encoding. Please save the file as UTF-8.", 415)

def sniff(raw: bytes, filename: str) -> str:
    """Validate real content, not only the extension."""
    kind = ALLOWED.get(os.path.splitext(filename or "")[1].lower())
    if not kind: raise ExtractError("Unsupported file type. Use PDF, DOCX or TXT.", 415)
    if not raw.strip(): raise ExtractError("File is empty.")
    if kind == "pdf" and not raw.startswith(b"%PDF"): raise ExtractError("File is not a valid PDF.", 415)
    if kind == "docx":
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                if "word/document.xml" not in z.namelist(): raise zipfile.BadZipFile()
        except zipfile.BadZipFile: raise ExtractError("File is not a valid DOCX.", 415)
    if kind == "pdf":
        try: pdf = pymupdf.open(stream=raw, filetype="pdf")
        except Exception: raise ExtractError("PDF file is corrupted.", 415)
        if pdf.needs_pass or pdf.is_encrypted: raise ExtractError("Encrypted PDFs are not supported.", 415)
    if kind == "txt": decode_text(raw)
    return kind

def extract_pages(raw: bytes, kind: str, max_pages: int):
    """Returns ([(page_or_None, text)], warnings)."""
    warnings: list[str] = []
    if kind == "txt": return [(None, decode_text(raw))], warnings
    if kind == "docx":
        try: d = docx.Document(io.BytesIO(raw))
        except Exception: raise ExtractError("DOCX file is corrupted.", 415)
        parts = [p.text for p in d.paragraphs if p.text.strip()]
        for t in d.tables:
            for row in t.rows: parts.append(" | ".join(c.text.strip() for c in row.cells))
        warnings.append("DOCX has no fixed pages; citations show the section, not a page number.")
        return [(None, "\n".join(parts))], warnings
    try: pdf = pymupdf.open(stream=raw, filetype="pdf")
    except Exception: raise ExtractError("PDF file is corrupted.", 415)
    if pdf.needs_pass or pdf.is_encrypted: raise ExtractError("Encrypted PDFs are not supported.", 415)
    if pdf.page_count > max_pages: raise ExtractError(f"PDF has {pdf.page_count} pages; the limit is {max_pages}.", 413)
    pages, empty = [], 0
    for i, pg in enumerate(pdf, start=1):
        t = pg.get_text().strip()
        if len(t) < 10:
            empty += 1; warnings.append(f"Page {i} has no extractable text (scanned page? OCR is not configured).")
        pages.append((i, t))
    if empty == len(pages): raise ExtractError("This PDF appears to be scanned images. OCR is required but not configured.")
    return pages, warnings
