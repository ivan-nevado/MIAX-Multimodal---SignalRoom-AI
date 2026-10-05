from __future__ import annotations

import base64
import json

import httpx
import pytest
import respx

from app.integrations.ai.base import (
    AIError,
    AIResponseError,
    AIUnavailableError,
    AudioInput,
    ChatRequest,
    ChatResult,
    ImageInput,
    SpeechResult,
)
from app.integrations.ai.gateway import AIGateway, RoleBinding, build_gateway, extract_json, split_for_speech
from app.integrations.ai.gemini import GeminiProvider
from app.integrations.ai.openrouter import OpenRouterProvider
from app.schemas.agents import AgentPlan


class ScriptedProvider:
    name = "scripted"

    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> ChatResult:
        self.requests.append(request)
        return ChatResult(
            text=self.replies.pop(0),
            model=request.model,
            provider="scripted",
            input_tokens=5,
            output_tokens=7,
            cost_usd=0.001,
            latency_ms=3,
        )

    async def synthesize(self, text: str, *, model: str, voice: str, style: str) -> SpeechResult:
        return SpeechResult(
            pcm=b"\x01\x00" * 100, sample_rate=24000, model=model, provider="scripted", latency_ms=1
        )


VALID_PLAN = json.dumps({"intent": "why_move", "agents": ["market"], "rationale": "x", "time_window_days": 7})


def gateway(provider: ScriptedProvider) -> AIGateway:
    return AIGateway({"reasoning": RoleBinding(provider, "m-reason"), "tts": RoleBinding(provider, "m-tts")})


async def test_structured_valid_records_usage() -> None:
    provider = ScriptedProvider([f"```json\n{VALID_PLAN}\n```"])
    gw = gateway(provider)
    plan = await gw.structured(AgentPlan, system="s", user="u", agent="orchestrator", purpose="plan")
    assert plan.intent == "why_move"
    assert provider.requests[0].json_mode is True
    assert "JSON Schema" in provider.requests[0].system
    usage = gw.tracker.records[0]
    assert (usage.model, usage.agent, usage.input_tokens, usage.cost_usd) == (
        "m-reason",
        "orchestrator",
        5,
        0.001,
    )


async def test_structured_retries_once_with_correction() -> None:
    provider = ScriptedProvider(['{"intent": "nonsense"}', VALID_PLAN])
    gw = gateway(provider)
    plan = await gw.structured(AgentPlan, system="s", user="u", agent="orchestrator", purpose="plan")
    assert plan.agents == ["market"]
    assert "not valid" in provider.requests[1].user
    assert [u.purpose for u in gw.tracker.records] == ["plan", "plan:retry"]


async def test_structured_fails_after_two_invalid_answers() -> None:
    gw = gateway(ScriptedProvider(["not json", "{}"]))
    with pytest.raises(AIResponseError):
        await gw.structured(AgentPlan, system="s", user="u", agent="orchestrator", purpose="plan")


async def test_unbound_role_raises_unavailable() -> None:
    gw = AIGateway({})
    assert not gw.available("vision")
    with pytest.raises(AIUnavailableError):
        await gw.text(system="s", user="u", agent="a", purpose="p", role="vision")


async def test_speech_concatenates_chunks_into_wav() -> None:
    gw = gateway(ScriptedProvider([]))
    out = await gw.speech("Para one.\n\n" + "Sentence. " * 300)
    assert out.wav[:4] == b"RIFF"
    assert out.duration_seconds >= 0
    assert all(r.purpose == "tts" for r in gw.tracker.records) and len(gw.tracker.records) >= 2


def test_extract_json_and_split_for_speech() -> None:
    assert extract_json('Here: {"a": 1} thanks') == {"a": 1}
    chunks = split_for_speech("A. " * 1000, max_chars=200)
    assert all(len(c) <= 205 for c in chunks) and len(chunks) > 5


def test_build_gateway_routing() -> None:
    models = {
        "reasoning": "openai/gpt-6-luna",
        "vision": "google/gemini-3.8-flash",
        "transcription": "google/gemini-3.8-flash",
        "tts": "openai/gpt-audio-mini",
        "gemini_tts": "gemini-3.8-flash-tts",
        "image": "google/gemini-3.1-flash-image",
    }
    common = {
        "models": models,
        "openrouter_base_url": "https://or/api/v1",
        "openai_base_url": "https://oa/v1",
        "gemini_base_url": "https://g/v1beta",
        "app_url": "http://x",
        "timeout": 5,
        "tts_voice": "sage",
    }
    gw = build_gateway(openrouter_key="k", openai_key=None, gemini_key=None, mode="auto", **common)
    assert gw.describe()["vision"] == {"provider": "openrouter", "model": "google/gemini-3.8-flash"}
    direct = build_gateway(openrouter_key=None, openai_key="o", gemini_key="g", mode="auto", **common)
    assert (
        direct.describe()["reasoning"]["provider"] == "openai"
        and direct.model_for("reasoning") == "gpt-6-luna"
    )
    assert direct.describe()["tts"]["model"] == "gemini-3.8-flash-tts"
    assert not direct.available("image")
    assert (
        build_gateway(openrouter_key=None, openai_key=None, gemini_key=None, mode="auto", **common).describe()
        == {}
    )


@respx.mock
async def test_openrouter_chat_with_image_and_audio_parts() -> None:
    route = respx.post("https://or.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "google/gemini-3.8-flash",
                "provider": "Google",
                "choices": [{"message": {"content": "{}"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2, "cost": 0.0002},
            },
        )
    )
    provider = OpenRouterProvider(api_key="k", base_url="https://or.test/v1")
    result = await provider.chat(
        ChatRequest(
            system="s",
            user="u",
            model="google/gemini-3.8-flash",
            json_mode=True,
            images=[ImageInput(b"png", "image/png")],
            audio=[AudioInput(b"wav", "audio/mpeg")],
        )
    )
    body = json.loads(route.calls[0].request.content)
    parts = body["messages"][1]["content"]
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert parts[2]["input_audio"]["format"] == "mp3"
    assert body["response_format"] == {"type": "json_object"}
    assert route.calls[0].request.headers["X-Title"] == "SignalRoom AI"
    assert (result.input_tokens, result.cost_usd, result.provider) == (10, 0.0002, "Google")


@respx.mock
async def test_openrouter_retries_429_then_fails_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.integrations.ai.openai_compatible.asyncio.sleep", _no_sleep)
    route = respx.post("https://or.test/v1/chat/completions").mock(
        return_value=httpx.Response(429, json={"error": {"message": "slow down"}})
    )
    provider = OpenRouterProvider(api_key="k", base_url="https://or.test/v1")
    with pytest.raises(AIError, match="429"):
        await provider.chat(ChatRequest(system="s", user="u", model="m"))
    assert route.call_count == 3


@respx.mock
async def test_openrouter_tts_stream_parsing() -> None:
    chunk = base64.b64encode(b"\x10\x00" * 50).decode()
    sse = (
        "".join(
            f"data: {json.dumps({'choices': [{'delta': {'audio': {'data': chunk}}}]})}\n\n" for _ in range(3)
        )
        + f"data: {json.dumps({'choices': [], 'usage': {'cost': 0.003}})}\n\ndata: [DONE]\n\n"
    )
    route = respx.post("https://or.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})
    )
    provider = OpenRouterProvider(api_key="k", base_url="https://or.test/v1")
    result = await provider.synthesize("Hello", model="openai/gpt-audio-mini", voice="sage", style="calm")
    body = json.loads(route.calls[0].request.content)
    assert body["modalities"] == ["text", "audio"] and body["stream"] is True
    assert len(result.pcm) == 300 and result.cost_usd == 0.003


@respx.mock
async def test_openrouter_image_generation() -> None:
    png = base64.b64encode(b"\x89PNG\r\n\x1a\nxx").decode()
    respx.post("https://or.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "images": [{"image_url": {"url": f"data:image/png;base64,{png}"}}],
                        }
                    }
                ]
            },
        )
    )
    result = await OpenRouterProvider(api_key="k", base_url="https://or.test/v1").generate_image(
        "card", model="img"
    )
    assert result.mime_type == "image/png" and result.data.startswith(b"\x89PNG")


@respx.mock
async def test_gemini_native_chat_and_tts() -> None:
    respx.post("https://g.test/v1beta/models/gemini-3.8-flash:generateContent").mock(
        return_value=httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}],
                "usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 2},
            },
        )
    )
    pcm = base64.b64encode(b"\x00\x01" * 10).decode()
    tts = respx.post("https://g.test/v1beta/models/gemini-3.8-flash-tts:generateContent").mock(
        return_value=httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"inlineData": {"data": pcm}}]}}]}
        )
    )
    provider = GeminiProvider(api_key="g", base_url="https://g.test/v1beta")
    result = await provider.chat(
        ChatRequest(
            system="s",
            user="u",
            model="google/gemini-3.8-flash",
            json_mode=True,
            audio=[AudioInput(b"a", "audio/wav")],
        )
    )
    assert result.text == '{"ok": true}' and result.input_tokens == 4
    speech = await provider.synthesize("hi", model="gemini-3.8-flash-tts", voice="Charon", style="calm")
    assert len(speech.pcm) == 20
    assert json.loads(tts.calls[0].request.content)["generationConfig"]["responseModalities"] == ["AUDIO"]


async def _no_sleep(*_: object) -> None:
    return None


@respx.mock
async def test_openrouter_video_part_and_embeddings() -> None:
    from app.integrations.ai.base import VideoInput

    chat = respx.post("https://or.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}], "usage": {}})
    )
    emb = respx.post("https://or.test/v1/embeddings").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "data": [{"index": 1, "embedding": [0.0, 1.0]}, {"index": 0, "embedding": [1.0, 0.0]}],
                    "usage": {"prompt_tokens": 8, "cost": 0.00001},
                },
            ),
            httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.5, 0.5]}], "usage": {}}),
            httpx.Response(200, json={"data": []}),
        ]
    )
    provider = OpenRouterProvider(api_key="k", base_url="https://or.test/v1")
    await provider.chat(
        ChatRequest(system="s", user="u", model="m", videos=[VideoInput(b"mp4", "video/mp4")])
    )
    part = json.loads(chat.calls[0].request.content)["messages"][1]["content"][1]
    assert part["type"] == "video_url" and part["video_url"]["url"].startswith("data:video/mp4;base64,")

    gw = AIGateway({"embedding": RoleBinding(provider, "google/gemini-embedding-2")})
    vectors = await gw.embed_texts(["first", "second"])
    assert vectors == [[1.0, 0.0], [0.0, 1.0]]  # re-ordered by index
    assert json.loads(emb.calls[0].request.content) == {
        "model": "google/gemini-embedding-2",
        "input": ["first", "second"],
    }
    assert await gw.embed_image(b"png", "image/png") == [0.5, 0.5]
    image_input = json.loads(emb.calls[1].request.content)["input"][0]
    assert image_input["content"][0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert [u.purpose for u in gw.tracker.records] == ["embedding_text", "embedding_image"]
    with pytest.raises(AIResponseError):
        await gw.embed_texts(["x"])
    with pytest.raises(AIUnavailableError):
        await AIGateway({}).embed_texts(["x"])
