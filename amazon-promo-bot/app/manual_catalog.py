import json
from pathlib import Path

from sqlalchemy.orm import Session

from .affiliate import build_affiliate_link, build_amazon_search_link
from .asin_utils import extract_asin_from_url, is_valid_asin
from .config import settings
from .models import ManualProduct


SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "manual_products_seed.json"


def load_seed_products() -> list[dict]:
    with SEED_PATH.open("r", encoding="utf-8") as seed_file:
        data = json.load(seed_file)

    if not isinstance(data, list):
        raise ValueError("O seed precisa ser uma lista de produtos")

    return data


def import_seed_products(db: Session) -> dict:
    seed_products = load_seed_products()
    inserted = 0
    skipped = 0

    for item in seed_products:
        title = _clean_required(item.get("title"), "title")
        author = _clean_optional(item.get("author"))
        format_preference = _clean_optional(item.get("format_preference")) or "any"

        duplicate = (
            db.query(ManualProduct)
            .filter(
                ManualProduct.title == title,
                ManualProduct.author == author,
                ManualProduct.format_preference == format_preference,
            )
            .first()
        )
        if duplicate:
            skipped += 1
            continue

        asin = _extract_seed_asin(item)
        search_query = _clean_required(item.get("amazon_search_query"), "amazon_search_query")
        affiliate_link = (
            build_affiliate_link(asin, settings.amazon_associate_tag) if asin else None
        )
        search_link = build_amazon_search_link(search_query, settings.amazon_associate_tag)

        product = ManualProduct(
            title=title,
            author=author,
            category=_clean_required(item.get("category"), "category"),
            subcategory=_clean_optional(item.get("subcategory")),
            template_type=_clean_required(item.get("template_type"), "template_type"),
            format_preference=format_preference,
            asin=asin,
            amazon_url=_clean_optional(item.get("amazon_url")),
            amazon_search_query=search_query,
            affiliate_link=affiliate_link,
            search_link=search_link,
            needs_asin=asin is None,
            adult_content=bool(item.get("adult_content", False)),
            priority=int(item.get("priority", 3)),
            active=bool(item.get("active", True)),
            notes=_clean_optional(item.get("notes")),
        )
        db.add(product)
        inserted += 1

    db.commit()
    return {
        "inserted": inserted,
        "skipped": skipped,
        "total_seed": len(seed_products),
    }


def update_product_asin(
    db: Session,
    product_id: int,
    amazon_url_or_asin: str,
) -> ManualProduct:
    product = db.get(ManualProduct, product_id)
    if not product:
        raise LookupError("Produto manual não encontrado")

    raw_value = amazon_url_or_asin.strip() if amazon_url_or_asin else ""
    asin = extract_asin_from_url(raw_value)
    if asin is None and is_valid_asin(raw_value):
        asin = raw_value.upper()

    if asin is None:
        raise ValueError("ASIN ou URL da Amazon inválido")

    product.asin = asin
    if raw_value.startswith(("http://", "https://")):
        product.amazon_url = raw_value
    product.affiliate_link = build_affiliate_link(asin, settings.amazon_associate_tag)
    product.needs_asin = False

    db.commit()
    db.refresh(product)
    return product


def _extract_seed_asin(item: dict) -> str | None:
    raw_asin = _clean_optional(item.get("asin"))
    if raw_asin and is_valid_asin(raw_asin):
        return raw_asin.upper()

    amazon_url = _clean_optional(item.get("amazon_url"))
    if amazon_url:
        return extract_asin_from_url(amazon_url)

    return None


def _clean_required(value: object, field_name: str) -> str:
    clean_value = _clean_optional(value)
    if not clean_value:
        raise ValueError(f"{field_name} é obrigatório no seed")
    return clean_value


def _clean_optional(value: object) -> str | None:
    if value is None:
        return None

    clean_value = str(value).strip()
    return clean_value or None
