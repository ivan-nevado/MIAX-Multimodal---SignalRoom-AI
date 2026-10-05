from __future__ import annotations

import io

from PIL import Image, ImageOps

MAX_SIDE = 1600


def preprocess_image(data: bytes, max_side: int = MAX_SIDE) -> tuple[bytes, str]:
    """Normalise orientation, strip metadata, downscale, re-encode (PNG keeps chart text crisp)."""
    with Image.open(io.BytesIO(data)) as original:
        img: Image.Image = ImageOps.exif_transpose(original) or original
        img.thumbnail((max_side, max_side))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), "image/png"


def sniff_image_mime(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
