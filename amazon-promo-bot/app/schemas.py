from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ManualProductRead(BaseModel):
    id: int
    title: str
    author: str | None = None
    category: str
    subcategory: str | None = None
    template_type: str
    format_preference: str | None = None
    asin: str | None = None
    amazon_url: str | None = None
    amazon_search_query: str
    affiliate_link: str | None = None
    search_link: str | None = None
    needs_asin: bool
    adult_content: bool
    priority: int
    active: bool
    notes: str | None = None
    current_price: float | None = None
    list_price: float | None = None
    currency: str | None = "BRL"
    discount_amount: float | None = None
    discount_percent: float | None = None
    availability: str | None = None
    deal_badge: str | None = None
    price_source: str | None = "none"
    last_price_checked_at: datetime | None = None
    price_error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ManualProductAsinUpdate(BaseModel):
    amazon_url_or_asin: str = Field(..., min_length=1)


class ManualProductMessageRead(BaseModel):
    product_id: int
    ready: bool
    message: str


class ImportSeedSummary(BaseModel):
    inserted: int
    skipped: int
    total_seed: int


class ManualProductActiveUpdate(BaseModel):
    active: bool


class DashboardSummary(BaseModel):
    total_products: int
    ready_products: int
    pending_asin: int
    active_products: int
    adult_content: int
    verified_promotions: int
    categories: dict[str, int]


class TopBookItem(BaseModel):
    id: int
    title: str
    author: str | None = None
    asin: str | None = None
    affiliate_link: str | None = None
    status_label: str
    price_label: str
    current_price: float | None = None
    list_price: float | None = None
    discount_percent: float | None = None
    last_price_checked_at: datetime | None = None
    template_type: str
    priority: int


class TopBookCategory(BaseModel):
    category: str
    label: str
    items: list[TopBookItem]


class DashboardTopBooks(BaseModel):
    mode: str
    title: str
    subtitle: str
    has_verified_prices: bool
    categories: list[TopBookCategory]


class DynamicProductsRead(BaseModel):
    items: list[dict]
    message: str


class AmazonIntegrationStatus(BaseModel):
    source_mode: str
    real_amazon_enabled: bool
    has_associate_tag: bool
    has_creators_api_credentials: bool
    can_fetch_live_prices: bool
    can_detect_real_promotions: bool
    message: str
    safe_mode: bool


class PriceRefreshRequest(BaseModel):
    only_ready: bool = True
    limit: int | None = Field(default=None, ge=1, le=100)


class PriceRefreshSummary(BaseModel):
    live_prices_enabled: bool
    updated: int
    skipped: int
    errors: list[str]


class SinglePriceRefreshResponse(BaseModel):
    product_id: int
    updated: bool
    message: str


class PromotionsRead(BaseModel):
    items: list[ManualProductRead]
    message: str
