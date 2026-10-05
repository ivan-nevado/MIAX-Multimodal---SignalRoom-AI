"""Renders the daily briefing email (HTML + plain text) with Jinja2 autoescaping."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas.briefings import Briefing

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
_env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html"]))


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    arrow = "▲" if value > 0 else "▼" if value < 0 else "■"
    return f"{arrow} {value:+.2f}%"


_env.filters["pct"] = _fmt_pct


def render_briefing_email(
    briefing: Briefing, *, frontend_url: str, audio_url: str | None
) -> tuple[str, str, str]:
    base = frontend_url.rstrip("/")
    link = f"{base}/app/briefing/{briefing.briefing_id}"
    settings_link = f"{base}/app/settings#briefing"
    source_by_id = {s.id: s for s in briefing.sources}
    sections = []
    for sec in briefing.sections[:3]:
        sources = [source_by_id[i] for i in sec.source_ids if i in source_by_id and source_by_id[i].url][:2]
        sections.append({"section": sec, "sources": sources})
    context = {
        "b": briefing,
        "sections": sections,
        "moves": briefing.watchlist_moves[:6],
        "link": link,
        "audio_url": audio_url,
        "settings_link": settings_link,
    }
    subject = f"SignalRoom · {briefing.headline or 'Your daily market briefing'}"
    html = _env.get_template("email/daily_briefing.html").render(**context)
    text = _env.get_template("email/daily_briefing.txt").render(**context)
    return subject, html, text
