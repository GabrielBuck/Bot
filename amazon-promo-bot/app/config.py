import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    # Valor apenas para desenvolvimento. Em producao, configure no .env.
    amazon_associate_tag: str = os.getenv("AMAZON_ASSOCIATE_TAG") or "tag-teste-20"
    amazon_source: str = os.getenv("AMAZON_SOURCE", "manual_fixed")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/promos.db")

    amazon_creators_api_enabled: bool = _get_bool_env(
        "AMAZON_CREATORS_API_ENABLED",
        False,
    )
    amazon_creators_api_public_key: str = os.getenv(
        "AMAZON_CREATORS_API_PUBLIC_KEY",
        "",
    )
    amazon_creators_api_private_key: str = os.getenv(
        "AMAZON_CREATORS_API_PRIVATE_KEY",
        "",
    )
    amazon_creators_api_partner_tag: str = os.getenv(
        "AMAZON_CREATORS_API_PARTNER_TAG",
        "",
    )
    amazon_marketplace: str = os.getenv("AMAZON_MARKETPLACE", "www.amazon.com.br")
    amazon_region: str = os.getenv("AMAZON_REGION", "br")
    amazon_live_price_limit: int = _get_int_env("AMAZON_LIVE_PRICE_LIMIT", 20)

    @property
    def has_associate_tag(self) -> bool:
        return bool(self.amazon_associate_tag.strip())

    @property
    def has_creators_api_credentials(self) -> bool:
        return all(
            [
                self.amazon_creators_api_public_key.strip(),
                self.amazon_creators_api_private_key.strip(),
                self.amazon_creators_api_partner_tag.strip(),
            ]
        )

    @property
    def can_fetch_live_prices(self) -> bool:
        # A integração real ainda não foi implementada. Mesmo com variáveis
        # preenchidas, preços reais só devem ser consultados quando o cliente
        # oficial da Creators API existir.
        real_integration_implemented = False
        return (
            self.amazon_creators_api_enabled
            and self.has_creators_api_credentials
            and real_integration_implemented
        )


settings = Settings()
