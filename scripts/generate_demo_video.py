"""Generate a synthetic investor-webinar video for the demo (fictional company, no copyrighted media).

Combines slides (title, the two pages of the synthetic results PDF and an outlook slide) with the
synthetic earnings-call audio into demo_data/northwind_webinar.mp4 (720p, 1 fps, H.264 + AAC).

Requires the demo assets (scripts/generate_demo_assets.py, scripts/generate_demo_audio.py) and the
tooling-only package `imageio-ffmpeg` (bundled ffmpeg binary; not needed by the app itself):
    pip install imageio-ffmpeg
    backend/.venv/Scripts/python scripts/generate_demo_video.py
"""

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import imageio_ffmpeg
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo_data"
W, H = 1280, 720
BG, INK, MUTED, VIOLET = (8, 9, 13), (245, 245, 247), (161, 161, 170), (139, 92, 246)


def text_slide(title: str, lines: list[str], footer: str = "Northwind Semiconductors (fictional) · Q3 FY2026 investor webinar") -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    big, mid, small = ImageFont.load_default(size=52), ImageFont.load_default(size=30), ImageFont.load_default(size=20)
    d.rectangle([80, 110, 92, 170], fill=VIOLET)
    d.text((115, 105), title, fill=INK, font=big)
    y = 230
    for line in lines:
        d.text((115, y), line, fill=INK if not line.startswith("  ") else MUTED, font=mid)
        y += 58
    d.text((80, H - 60), footer, fill=MUTED, font=small)
    return img


def pdf_slide(page_index: int) -> Image.Image:
    pdf = pdfium.PdfDocument(str(DEMO / "northwind_q3_fy2026_results.pdf"))
    page = pdf[page_index].render(scale=1.15).to_pil().convert("RGB")
    pdf.close()
    page.thumbnail((W - 80, H - 40))
    img = Image.new("RGB", (W, H), (235, 235, 240))
    img.paste(page, ((W - page.width) // 2, (H - page.height) // 2))
    return img


def main() -> None:
    audio = DEMO / "earnings_call.wav"
    if not audio.exists():
        sys.exit("Run scripts/generate_demo_audio.py first")
    with wave.open(str(audio)) as w:
        duration = w.getnframes() / w.getframerate()
    # (slide, seconds on screen) — roughly follows the call script
    slides = [
        (text_slide("Q3 FY2026 Results", ["Record revenue of $4.2B (+31% YoY)", "Data center revenue +44%", "Webinar with CEO Dana Reyes and CFO Marcus Lin"]), 14),
        (pdf_slide(0), 32),
        (pdf_slide(1), 34),
        (text_slide("Q4 FY2026 Outlook", ["Revenue: $4.0B - $4.2B", "  includes ~$300M impact from new export licences", "Gross margin: ~60%", "New $1.0B share repurchase program", "Largest customer = 22% of revenue"]), 0),
    ]
    used = sum(s for _, s in slides[:-1])
    slides[-1] = (slides[-1][0], max(int(duration - used) + 1, 10))

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory() as tmp:
        concat = Path(tmp) / "slides.txt"
        entries = []
        for i, (img, secs) in enumerate(slides):
            path = Path(tmp) / f"s{i}.png"
            img.save(path)
            entries.append(f"file '{path.as_posix()}'\nduration {secs}")
        entries.append(f"file '{(Path(tmp) / f's{len(slides) - 1}.png').as_posix()}'")
        concat.write_text("\n".join(entries), encoding="utf-8")
        out = DEMO / "northwind_webinar.mp4"
        cmd = [
            ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-i", str(audio),
            "-vf", "fps=1,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
            "-c:a", "aac", "-b:a", "64k", "-shortest", "-movflags", "+faststart", str(out),
        ]
        subprocess.run(cmd, check=True)
    print(f"Wrote {out} ({out.stat().st_size / 1e6:.1f} MB, ~{duration:.0f}s)")


if __name__ == "__main__":
    _ = io  # keep imports explicit for readers
    main()
