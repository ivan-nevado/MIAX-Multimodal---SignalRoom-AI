"""PDF helpers: text extraction first, then render only the most relevant pages for vision."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

_FIN_TERMS = [
    "revenue",
    "net income",
    "operating income",
    "gross margin",
    "operating margin",
    "earnings per share",
    "eps",
    "guidance",
    "outlook",
    "cash flow",
    "balance sheet",
    "total assets",
    "liabilities",
    "cash and cash equivalents",
    "debt",
    "segment",
    "fiscal",
    "quarter",
    "year-over-year",
    "risk factors",
    "ingresos",
    "beneficio",
    "resultado",
    "deuda",
    "margen",
]
_NUMBER_RE = re.compile(r"\$?\(?\d[\d,\.]*\)?\s?(%|million|billion|bn|m\b)?", re.I)


@dataclass
class PdfPage:
    number: int  # 1-based
    text: str


@dataclass
class PdfContent:
    page_count: int
    pages: list[PdfPage]

    @property
    def total_chars(self) -> int:
        return sum(len(p.text) for p in self.pages)


def extract_pdf_text(data: bytes, max_pages: int = 400) -> PdfContent:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages: list[PdfPage] = []
    for idx, page in enumerate(reader.pages[:max_pages]):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(PdfPage(number=idx + 1, text=" ".join(text.split())))
    return PdfContent(page_count=len(reader.pages), pages=pages)


def score_page(page: PdfPage, question_terms: set[str]) -> float:
    text = page.text.lower()
    if not text:
        return 0.0
    fin = sum(text.count(term) for term in _FIN_TERMS)
    numbers = len(_NUMBER_RE.findall(text))
    question = sum(text.count(t) for t in question_terms)
    density = numbers / max(len(text) / 1000, 1)
    return fin * 2.0 + question * 3.0 + min(density, 40) * 0.5


def select_relevant_pages(content: PdfContent, question: str, limit: int) -> list[PdfPage]:
    terms = {w for w in re.findall(r"[a-záéíóúñ]{4,}", question.lower())}
    ranked = sorted(content.pages, key=lambda p: score_page(p, terms), reverse=True)
    chosen = [p for p in ranked[:limit] if p.text] or content.pages[:limit]
    return sorted(chosen, key=lambda p: p.number)


def is_table_heavy(page: PdfPage) -> bool:
    """Pages dense in numbers are where text extraction loses layout → worth a vision pass."""
    if not page.text:
        return True  # scanned page: only vision can read it
    numbers = len(_NUMBER_RE.findall(page.text))
    return numbers / max(len(page.text.split()), 1) > 0.18


def render_pages(data: bytes, page_numbers: list[int], scale: float = 1.6) -> list[tuple[int, bytes]]:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    rendered: list[tuple[int, bytes]] = []
    try:
        for number in page_numbers:
            if number < 1 or number > len(pdf):
                continue
            page = pdf[number - 1]
            image = page.render(scale=scale).to_pil()
            buf = io.BytesIO()
            image.convert("RGB").save(buf, format="JPEG", quality=82)
            rendered.append((number, buf.getvalue()))
    finally:
        pdf.close()
    return rendered
