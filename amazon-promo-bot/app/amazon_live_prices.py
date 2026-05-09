from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .config import Settings, settings


class LivePriceUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class AmazonLivePriceResult:
    asin: str
    title: str | None
    current_price: float | None
    list_price: float | None
    currency: str | None
    discount_amount: float | None
    discount_percent: float | None
    availability: str | None
    deal_badge: str | None
    source: str
    checked_at: datetime
    raw_data: dict[str, Any] | None = None


class AmazonLivePriceService:
    def is_configured(self) -> bool:
        raise NotImplementedError

    def fetch_price_by_asin(self, asin: str) -> AmazonLivePriceResult:
        raise NotImplementedError


class CreatorsApiPriceService(AmazonLivePriceService):
    """Placeholder para integração oficial futura.

    A implementação real deve ser adicionada apenas quando as credenciais
    oficiais da Creators API estiverem disponíveis, usando a documentação
    oficial da Amazon. Este módulo não faz scraping, não automatiza navegador
    e não simula preço.
    """

    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def is_configured(self) -> bool:
        return self.settings.amazon_creators_api_enabled and (
            self.settings.has_creators_api_credentials
        )

    def fetch_price_by_asin(self, asin: str) -> AmazonLivePriceResult:
        raise LivePriceUnavailableError(
            "Creators API ainda não configurada/implementada."
        )
