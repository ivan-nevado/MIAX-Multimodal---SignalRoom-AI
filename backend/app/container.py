"""Composition root: builds every adapter from Settings exactly once.

This is the only module that knows which concrete implementation (local vs AWS,
OpenRouter vs direct providers) is in use. Tests replace it with `set_container`.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

from app.agents.base import AgentContext
from app.config.settings import Settings, get_settings
from app.integrations.ai.base import UsageTracker
from app.integrations.ai.gateway import AIGateway, build_gateway
from app.integrations.email.base import EmailSender

if TYPE_CHECKING:
    from app.services.search_index import SearchIndexService
from app.integrations.financial.base import FinancialDataProvider
from app.integrations.macro.base import MacroDataProvider
from app.integrations.market.base import MarketDataProvider
from app.integrations.news.base import NewsProvider
from app.integrations.news.composite import CompositeNewsProvider
from app.integrations.queue.base import QueueBackend
from app.integrations.storage.base import StorageBackend
from app.repositories.base import Repositories


@dataclass
class Container:
    settings: Settings

    # ------------------------------------------------------------------ persistence
    @cached_property
    def repos(self) -> Repositories:
        s = self.settings
        if s.backend_mode == "aws":
            from app.repositories import dynamodb as d

            tables = d.DynamoTables(s.dynamodb_table_prefix, s.aws_region, s.aws_endpoint_url)
            return Repositories(
                users=d.DynamoUserRepository(tables),
                credentials=d.DynamoCredentialRepository(tables),
                watchlists=d.DynamoWatchlistRepository(tables),
                investigations=d.DynamoInvestigationRepository(tables),
                events=d.DynamoEventRepository(tables),
                briefings=d.DynamoBriefingRepository(tables),
                deliveries=d.DynamoDeliveryRepository(tables),
                uploads=d.DynamoUploadRepository(tables),
                cache=d.DynamoCacheRepository(tables),
            )
        from app.repositories import local as loc

        base = None if s.app_env == "test" else s.local_data_dir / "db"
        return Repositories(
            users=loc.LocalUserRepository(base),
            credentials=loc.LocalCredentialRepository(base),
            watchlists=loc.LocalWatchlistRepository(base),
            investigations=loc.LocalInvestigationRepository(base),
            events=loc.LocalEventRepository(base),
            briefings=loc.LocalBriefingRepository(base),
            deliveries=loc.LocalDeliveryRepository(base),
            uploads=loc.LocalUploadRepository(base),
            cache=loc.MemoryCacheRepository(),
        )

    @cached_property
    def storage(self) -> StorageBackend:
        s = self.settings
        if s.backend_mode == "aws":
            from app.integrations.storage.s3 import S3Storage

            return S3Storage(s.s3_bucket or "", s.aws_region, s.aws_endpoint_url)
        from app.integrations.storage.local import LocalStorage

        return LocalStorage(
            s.local_data_dir / "storage",
            signing_secret=s.local_jwt_secret.get_secret_value(),
            public_base_url=s.app_base_url,
        )

    @cached_property
    def queue(self) -> QueueBackend:
        s = self.settings
        if s.backend_mode == "aws":
            from app.integrations.queue.sqs import SQSQueue

            return SQSQueue(
                {
                    "investigations": s.sqs_investigation_queue_url or "",
                    "briefings": s.sqs_briefing_queue_url or "",
                },
                s.aws_region,
                s.aws_endpoint_url,
            )
        from app.integrations.queue.local import LocalQueue

        return LocalQueue()

    @cached_property
    def email(self) -> EmailSender:
        s = self.settings
        if s.effective_email_backend == "ses" and s.ses_from_email:
            from app.integrations.email.ses import SESEmailSender

            return SESEmailSender(s.ses_from_email, s.aws_region, s.aws_endpoint_url)
        from app.integrations.email.local import LocalOutboxSender

        return LocalOutboxSender(s.local_data_dir / "outbox")

    # ------------------------------------------------------------------ AI
    @cached_property
    def ai(self) -> AIGateway:
        s = self.settings
        return build_gateway(
            openrouter_key=s.secret("openrouter_api_key"),
            openai_key=s.secret("openai_api_key"),
            gemini_key=s.secret("gemini_api_key"),
            mode=s.ai_provider,
            models={
                "reasoning": s.openai_model,
                "vision": s.gemini_multimodal_model,
                "transcription": s.gemini_transcribe_model,
                "tts": s.tts_model,
                "gemini_tts": s.gemini_tts_model,
                "image": s.image_model,
                "embedding": s.embedding_model,
            },
            openrouter_base_url=s.openrouter_base_url,
            openai_base_url=s.openai_base_url,
            gemini_base_url=s.gemini_base_url,
            app_url=s.frontend_url,
            timeout=s.ai_timeout_seconds,
            tts_voice=s.tts_voice,
        )

    # ------------------------------------------------------------------ data providers
    @cached_property
    def market(self) -> MarketDataProvider:
        from app.integrations.market.fallback import FallbackMarketDataProvider
        from app.integrations.market.yahoo import YahooMarketDataProvider

        providers: list[MarketDataProvider] = [YahooMarketDataProvider(self.repos.cache)]
        key = self.settings.secret("alphavantage_api_key")
        if key:
            from app.integrations.market.alpha_vantage import AlphaVantageMarketDataProvider

            providers.append(AlphaVantageMarketDataProvider(key, self.repos.cache))
        return FallbackMarketDataProvider(providers)

    @cached_property
    def news(self) -> CompositeNewsProvider:
        from app.integrations.news.yahoo import YahooNewsProvider

        cache = self.repos.cache
        providers: list[NewsProvider] = []
        timeline = None
        if self.settings.gdelt_enabled:
            from app.integrations.news.gdelt import GdeltNewsProvider

            gdelt = GdeltNewsProvider(cache, min_interval=self.settings.gdelt_min_interval_seconds)
            providers.append(gdelt)
            timeline = gdelt
        providers.append(YahooNewsProvider(cache))
        key = self.settings.secret("alphavantage_api_key")
        if key:
            from app.integrations.news.alpha_vantage import AlphaVantageNewsProvider

            providers.append(AlphaVantageNewsProvider(key, cache))
        return CompositeNewsProvider(providers, timeline)

    @cached_property
    def financial(self) -> FinancialDataProvider | None:
        from app.integrations.financial.sec import SecFinancialDataProvider

        if not self.settings.sec_user_agent:
            return None
        return SecFinancialDataProvider(self.settings.sec_user_agent, self.repos.cache)

    @cached_property
    def macro_providers(self) -> list[MacroDataProvider]:
        from app.integrations.macro.market_context import MarketContextProvider

        providers: list[MacroDataProvider] = [MarketContextProvider(self.market)]
        key = self.settings.secret("fred_api_key")
        if key:
            from app.integrations.macro.fred import FredMacroProvider

            providers.append(FredMacroProvider(key, self.repos.cache))
        return providers

    def agent_context(self, tracker: UsageTracker | None = None) -> AgentContext:
        return AgentContext(
            ai=self.ai.with_tracker(tracker) if tracker else self.ai,
            market=self.market,
            news=self.news,
            financial=self.financial,
            macro_providers=self.macro_providers,
            storage=self.storage,
            settings=self.settings,
        )

    def search_index(self, tracker: UsageTracker | None = None) -> SearchIndexService:
        from app.services.search_index import SearchIndexService

        return SearchIndexService(
            self.repos, self.storage, self.ai.with_tracker(tracker) if tracker else self.ai
        )


_container: Container | None = None
_lock = threading.Lock()


def get_container() -> Container:
    global _container
    if _container is None:
        with _lock:
            if _container is None:
                _container = Container(get_settings())
    return _container


def set_container(container: Container | None) -> None:
    global _container
    _container = container
