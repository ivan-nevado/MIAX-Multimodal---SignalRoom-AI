"""Generate demo upload files (no copyrighted material):

* demo_data/northwind_q3_fy2026_results.pdf — a synthetic 2-page earnings release for a
  FICTIONAL company (text page + financial table + bar chart), written as a raw PDF.
* demo_data/nvda_chart.png — a candlestick chart drawn from real Yahoo Finance data
  (via the backend's market data adapter) for the "Analyze this chart" demo.

Usage (from the repo root):  backend/.venv/Scripts/python scripts/generate_demo_assets.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
OUT = ROOT / "demo_data"


# ----------------------------------------------------------------------------- PDF
def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _text(x: float, y: float, size: float, text: str, bold: bool = False) -> str:
    font = "F2" if bold else "F1"
    return f"BT /{font} {size} Tf {x} {y} Td ({_esc(text)}) Tj ET\n"


def build_pdf(pages: list[str]) -> bytes:
    objects: list[bytes] = []
    n_pages = len(pages)
    page_ids = [5 + i * 2 for i in range(n_pages)]
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    for i, content in enumerate(pages):
        stream = content.encode("latin-1")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {page_ids[i] + 1} 0 R >>".encode()
        )
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{idx} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def earnings_release_pdf() -> bytes:
    p1 = _text(50, 740, 9, "FICTIONAL COMPANY - SYNTHETIC DEMO DOCUMENT FOR SIGNALROOM AI")
    p1 += _text(50, 710, 20, "Northwind Semiconductors Reports Third Quarter Fiscal 2026 Results", bold=True)
    lines = [
        "SANTA CLARA, Calif. - Northwind Semiconductors (fictional) today reported revenue for the third quarter",
        "of fiscal 2026 of $4.2 billion, up 31% from a year ago and up 6% from the previous quarter.",
        "",
        "Highlights",
        "- Data center revenue was a record $2.94 billion, up 44% year over year.",
        "- Gross margin was 61.5%, down 1.2 percentage points sequentially due to higher packaging costs.",
        "- Operating income was $1.3 billion; diluted earnings per share were $1.12.",
        "- Cash and cash equivalents were $5.8 billion; long-term debt was $2.1 billion.",
        "- The Board approved a new $1.0 billion share repurchase program.",
        "",
        "Outlook for the fourth quarter of fiscal 2026",
        "- Revenue is expected to be between $4.0 billion and $4.2 billion, including an estimated",
        "  $300 million impact from new export licence requirements for advanced chips.",
        "- Gross margin is expected to be approximately 60%.",
        "",
        "Risk factors",
        "- New export licence requirements may further limit shipments to certain regions.",
        "- Our largest cloud customer represented 22% of quarterly revenue (customer concentration).",
        "- Advanced packaging capacity remains constrained across the industry.",
        "",
        "\"We delivered record data center revenue while navigating a changing regulatory environment,\"",
        "said Dana Reyes, Chief Executive Officer (fictional).",
    ]
    y = 670
    for line in lines:
        bold = line in ("Highlights", "Risk factors") or line.startswith("Outlook")
        p1 += _text(50, y, 11, line, bold=bold)
        y -= 18

    p2 = _text(50, 740, 9, "FICTIONAL COMPANY - SYNTHETIC DEMO DOCUMENT FOR SIGNALROOM AI")
    p2 += _text(50, 710, 16, "Condensed Consolidated Statement of Income (unaudited, $ millions)", bold=True)
    rows = [
        ("", "Q3 FY2026", "Q2 FY2026", "Q3 FY2025"),
        ("Revenue", "4,200", "3,962", "3,206"),
        ("  Data center", "2,940", "2,690", "2,042"),
        ("  Client & gaming", "1,260", "1,272", "1,164"),
        ("Gross profit", "2,583", "2,484", "1,955"),
        ("Gross margin", "61.5%", "62.7%", "61.0%"),
        ("Operating income", "1,302", "1,228", "897"),
        ("Net income", "1,071", "1,010", "735"),
        ("Diluted EPS ($)", "1.12", "1.06", "0.77"),
    ]
    y = 670
    p2 += "0.6 w 50 685 m 560 685 l S\n"
    for i, row in enumerate(rows):
        bold = i == 0
        p2 += _text(55, y, 11, row[0], bold=bold or row[0] in ("Revenue", "Net income"))
        for j, cell in enumerate(row[1:]):
            p2 += _text(300 + j * 90, y, 11, cell, bold=bold)
        y -= 22
        if i in (0, len(rows) - 1):
            p2 += f"0.6 w 50 {y + 14} m 560 {y + 14} l S\n"
    p2 += _text(50, 430, 13, "Quarterly revenue ($ millions)", bold=True)
    bars = [("Q3 FY25", 3206), ("Q4 FY25", 3410), ("Q1 FY26", 3655), ("Q2 FY26", 3962), ("Q3 FY26", 4200)]
    for i, (label, value) in enumerate(bars):
        x, h = 80 + i * 95, value / 4200 * 220
        shade = "0.55 0.36 0.96 rg" if i == len(bars) - 1 else "0.6 0.6 0.65 rg"
        p2 += f"{shade} {x} 150 55 {h:.1f} re f 0 0 0 rg\n"
        p2 += _text(x + 4, 150 + h + 6, 10, f"{value:,}")
        p2 += _text(x + 2, 132, 10, label)
    return build_pdf([p1, p2])


# ----------------------------------------------------------------------------- chart
async def nvda_chart() -> bytes:
    import io

    from PIL import Image, ImageDraw, ImageFont

    from app.container import get_container

    history = (await get_container().market.get_history("NVDA", "6mo"))[-70:]
    w, h, pad_l, pad_r, pad_t, pad_b = 1280, 720, 70, 90, 70, 60
    img = Image.new("RGB", (w, h), (13, 15, 21))
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=16)
    title = ImageFont.load_default(size=24)
    lo, hi = min(p.low for p in history), max(p.high for p in history)
    span = hi - lo or 1

    def y(v: float) -> float:
        return pad_t + (hi - v) / span * (h - pad_t - pad_b)

    for i in range(6):
        val = lo + span * i / 5
        d.line([(pad_l, y(val)), (w - pad_r, y(val))], fill=(38, 41, 54))
        d.text((w - pad_r + 8, y(val) - 8), f"{val:,.0f}", fill=(161, 161, 170), font=font)
    step = (w - pad_l - pad_r) / len(history)
    closes = []
    for i, p in enumerate(history):
        x = pad_l + step * (i + 0.5)
        color = (34, 197, 94) if p.close >= p.open else (239, 68, 68)
        d.line([(x, y(p.high)), (x, y(p.low))], fill=color, width=1)
        top, bottom = sorted((y(p.open), y(p.close)))
        d.rectangle([x - step * 0.32, top, x + step * 0.32, max(bottom, top + 1)], fill=color)
        closes.append(p.close)
        if i % 14 == 0:
            d.text((x - 30, h - pad_b + 12), p.time, fill=(113, 113, 122), font=font)
    ma = [sum(closes[max(0, i - 19) : i + 1]) / len(closes[max(0, i - 19) : i + 1]) for i in range(len(closes))]
    d.line([(pad_l + step * (i + 0.5), y(v)) for i, v in enumerate(ma)], fill=(139, 92, 246), width=2)
    d.text((pad_l, 20), "NVDA - daily candles with 20-day moving average (purple)", fill=(245, 245, 247), font=title)
    d.text((pad_l, h - 26), f"Source: Yahoo Finance via yfinance, last bar {history[-1].time}. Generated for SignalRoom demo.", fill=(113, 113, 122), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def main() -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "northwind_q3_fy2026_results.pdf").write_bytes(earnings_release_pdf())
    print("Wrote demo_data/northwind_q3_fy2026_results.pdf")
    (OUT / "nvda_chart.png").write_bytes(await nvda_chart())
    print("Wrote demo_data/nvda_chart.png")


if __name__ == "__main__":
    asyncio.run(main())
