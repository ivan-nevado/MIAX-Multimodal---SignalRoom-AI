from __future__ import annotations

import io
import wave

_MIME_TO_FORMAT = {
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/aac": "aac",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
    "audio/x-flac": "flac",
}


def audio_format_for_mime(mime: str) -> str:
    return _MIME_TO_FORMAT.get(mime.lower().split(";")[0], "wav")


def pcm16_to_wav(pcm: bytes, sample_rate: int = 24000, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return buf.getvalue()


def pcm16_duration_seconds(pcm: bytes, sample_rate: int = 24000, channels: int = 1) -> float:
    return len(pcm) / (2 * channels * sample_rate)


def silence(seconds: float, sample_rate: int = 24000) -> bytes:
    return b"\x00\x00" * int(seconds * sample_rate)
