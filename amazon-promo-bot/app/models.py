from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import validates

from .database import Base


class ManualProduct(Base):
    __tablename__ = "manual_products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(255), nullable=True)
    category = Column(String(120), nullable=False, index=True)
    subcategory = Column(String(120), nullable=True)
    template_type = Column(String(60), nullable=False, default="padrao", index=True)
    format_preference = Column(String(30), nullable=True)
    asin = Column(String(10), nullable=True, index=True)
    amazon_url = Column(Text, nullable=True)
    amazon_search_query = Column(Text, nullable=False)
    affiliate_link = Column(Text, nullable=True)
    search_link = Column(Text, nullable=True)
    needs_asin = Column(Boolean, nullable=False, default=True, index=True)
    adult_content = Column(Boolean, nullable=False, default=False)
    priority = Column(Integer, nullable=False, default=3, index=True)
    active = Column(Boolean, nullable=False, default=True, index=True)
    notes = Column(Text, nullable=True)
    current_price = Column(Float, nullable=True)
    list_price = Column(Float, nullable=True)
    currency = Column(String(8), nullable=True, default="BRL")
    discount_amount = Column(Float, nullable=True)
    discount_percent = Column(Float, nullable=True)
    availability = Column(String(120), nullable=True)
    deal_badge = Column(String(120), nullable=True)
    price_source = Column(String(40), nullable=True, default="none")
    last_price_checked_at = Column(DateTime, nullable=True)
    price_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    @validates("asin")
    def validate_asin(self, key: str, value: str | None) -> str | None:
        clean_value = value.strip() if value else None
        self.needs_asin = clean_value is None
        return clean_value
