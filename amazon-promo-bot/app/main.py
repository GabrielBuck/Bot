import csv
import io
from collections.abc import Sequence
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, inspect, or_, text
from sqlalchemy.orm import Session

from .amazon_live_prices import CreatorsApiPriceService, LivePriceUnavailableError
from .config import settings
from .database import Base, engine, get_db
from .manual_catalog import import_seed_products, update_product_asin
from .messages import build_manual_product_message
from .models import ManualProduct
from .scanner import list_ready_manual_products
from .schemas import (
    AmazonIntegrationStatus,
    DashboardSummary,
    DashboardTopBooks,
    DynamicProductsRead,
    ImportSeedSummary,
    ManualProductActiveUpdate,
    ManualProductAsinUpdate,
    ManualProductMessageRead,
    ManualProductRead,
    PriceRefreshRequest,
    PriceRefreshSummary,
    PromotionsRead,
    SinglePriceRefreshResponse,
)


APP_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
TOP_CATEGORY_ORDER = [
    "romantasia",
    "romance_contemporaneo",
    "dark_romance",
    "thriller",
    "ficcao",
    "romance_esportivo",
    "nacional_romance",
    "nacional_kindle",
]
TOP_CATEGORY_LABELS = {
    "romantasia": "Romantasia",
    "romance_contemporaneo": "Romance contempor\u00e2neo",
    "dark_romance": "Dark romance",
    "thriller": "Thriller",
    "ficcao": "Fic\u00e7\u00e3o",
    "romance_esportivo": "Romance esportivo",
    "nacional_romance": "Nacional romance",
    "nacional_kindle": "Nacional Kindle",
}
TOP_READY_TITLE = "Top livros para checar hoje"
TOP_READY_SUBTITLE = (
    "Sugest\u00f5es com link pronto para voc\u00ea abrir e conferir manualmente na Amazon. "
    "Pre\u00e7os ainda n\u00e3o foram verificados automaticamente."
)
TOP_PROMOTIONS_TITLE = "Top promo\u00e7\u00f5es de livros para hoje"
TOP_PROMOTIONS_SUBTITLE = "Livros com pre\u00e7o e desconto verificados pela fonte oficial."
PRICE_UNAVAILABLE_MESSAGE = (
    "Preço real não consultado: Creators API ainda não configurada/implementada."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_price_columns()
    yield


app = FastAPI(title="Amazon Promo Bot", version="0.4.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


@app.get("/", include_in_schema=False)
def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "associate_tag_masked": _mask_associate_tag(settings.amazon_associate_tag),
            "amazon_source": settings.amazon_source,
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/integrations/amazon/status", response_model=AmazonIntegrationStatus)
def amazon_integration_status() -> dict:
    return _amazon_status_payload()


@app.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)) -> dict:
    total_products = db.query(func.count(ManualProduct.id)).scalar() or 0
    ready_products = (
        db.query(func.count(ManualProduct.id))
        .filter(
            ManualProduct.active.is_(True),
            ManualProduct.needs_asin.is_(False),
            ManualProduct.affiliate_link.isnot(None),
        )
        .scalar()
        or 0
    )
    pending_asin = (
        db.query(func.count(ManualProduct.id))
        .filter(ManualProduct.needs_asin.is_(True))
        .scalar()
        or 0
    )
    active_products = (
        db.query(func.count(ManualProduct.id))
        .filter(ManualProduct.active.is_(True))
        .scalar()
        or 0
    )
    adult_content = (
        db.query(func.count(ManualProduct.id))
        .filter(ManualProduct.adult_content.is_(True))
        .scalar()
        or 0
    )
    verified_promotions = _promotions_query(db).count()
    category_rows = (
        db.query(ManualProduct.category, func.count(ManualProduct.id))
        .group_by(ManualProduct.category)
        .order_by(ManualProduct.category.asc())
        .all()
    )

    return {
        "total_products": total_products,
        "ready_products": ready_products,
        "pending_asin": pending_asin,
        "active_products": active_products,
        "adult_content": adult_content,
        "verified_promotions": verified_promotions,
        "categories": {category: count for category, count in category_rows},
    }


@app.get("/dashboard/top-books", response_model=DashboardTopBooks)
def dashboard_top_books(
    max_per_category: int = Query(default=2, ge=1, le=10),
    db: Session = Depends(get_db),
) -> dict:
    verified_products = _promotions_query(db).all()
    if verified_products:
        products = sorted(
            verified_products,
            key=lambda product: (
                _category_sort_key(product.category),
                -(product.discount_percent or 0),
                product.title.lower(),
            ),
        )
        categories = _top_books_categories(
            products=products,
            max_per_category=max_per_category,
            mode="verified_promotions",
        )
        return {
            "mode": "verified_promotions",
            "title": TOP_PROMOTIONS_TITLE,
            "subtitle": TOP_PROMOTIONS_SUBTITLE,
            "has_verified_prices": True,
            "categories": categories,
        }

    ready_products = (
        db.query(ManualProduct)
        .filter(
            ManualProduct.active.is_(True),
            ManualProduct.needs_asin.is_(False),
            ManualProduct.affiliate_link.isnot(None),
        )
        .all()
    )
    products = sorted(
        ready_products,
        key=lambda product: (
            _category_sort_key(product.category),
            product.priority,
            product.title.lower(),
        ),
    )

    return {
        "mode": "ready_links",
        "title": TOP_READY_TITLE,
        "subtitle": TOP_READY_SUBTITLE,
        "has_verified_prices": False,
        "categories": _top_books_categories(
            products=products,
            max_per_category=max_per_category,
            mode="ready_links",
        ),
    }


@app.get("/dynamic-products", response_model=DynamicProductsRead)
def dynamic_products() -> dict:
    return {
        "items": [],
        "message": "Busca dinâmica ainda não implementada nesta V1.",
    }


@app.post("/manual-products/import-seed", response_model=ImportSeedSummary)
def import_manual_seed(db: Session = Depends(get_db)) -> dict:
    return import_seed_products(db)


@app.get("/manual-products/ready", response_model=list[ManualProductRead])
def list_ready_products(db: Session = Depends(get_db)) -> list[ManualProduct]:
    return list_ready_manual_products(db)


@app.get("/manual-products", response_model=list[ManualProductRead])
def list_manual_products(
    needs_asin: bool | None = Query(default=None),
    category: str | None = Query(default=None),
    template_type: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Sequence[ManualProduct]:
    query = db.query(ManualProduct)

    if needs_asin is not None:
        query = query.filter(ManualProduct.needs_asin.is_(needs_asin))
    if category:
        query = query.filter(ManualProduct.category == category)
    if template_type:
        query = query.filter(ManualProduct.template_type == template_type)
    if active is not None:
        query = query.filter(ManualProduct.active.is_(active))

    return query.order_by(ManualProduct.priority.asc(), ManualProduct.title.asc()).all()


@app.patch("/manual-products/{product_id}/asin", response_model=ManualProductRead)
def update_manual_product_asin(
    product_id: int,
    payload: ManualProductAsinUpdate,
    db: Session = Depends(get_db),
) -> ManualProduct:
    try:
        return update_product_asin(db, product_id, payload.amazon_url_or_asin)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch("/manual-products/{product_id}/active", response_model=ManualProductRead)
def update_manual_product_active(
    product_id: int,
    payload: ManualProductActiveUpdate,
    db: Session = Depends(get_db),
) -> ManualProduct:
    product = db.get(ManualProduct, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="produto manual nao encontrado",
        )

    product.active = payload.active
    db.commit()
    db.refresh(product)
    return product


@app.get("/manual-products/{product_id}/message", response_model=ManualProductMessageRead)
def get_manual_product_message(
    product_id: int,
    db: Session = Depends(get_db),
) -> dict:
    product = db.get(ManualProduct, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="produto manual nao encontrado",
        )

    ready = bool(product.active and not product.needs_asin and product.affiliate_link)
    return {
        "product_id": product.id,
        "ready": ready,
        "message": build_manual_product_message(product),
    }


@app.post("/prices/refresh", response_model=PriceRefreshSummary)
def refresh_prices(
    payload: PriceRefreshRequest | None = None,
    db: Session = Depends(get_db),
) -> dict:
    request_payload = payload or PriceRefreshRequest()
    limit = request_payload.limit or settings.amazon_live_price_limit
    products = _price_refresh_candidates(db, request_payload.only_ready, limit)
    service = CreatorsApiPriceService()

    if not settings.can_fetch_live_prices or not service.is_configured():
        for product in products:
            product.price_error = PRICE_UNAVAILABLE_MESSAGE
            product.price_source = product.price_source or "none"
        db.commit()
        return {
            "live_prices_enabled": False,
            "updated": 0,
            "skipped": len(products),
            "errors": [PRICE_UNAVAILABLE_MESSAGE],
        }

    updated = 0
    errors: list[str] = []
    for product in products:
        try:
            result = service.fetch_price_by_asin(product.asin or "")
        except LivePriceUnavailableError as exc:
            product.price_error = str(exc)
            errors.append(str(exc))
            continue

        _apply_live_price_result(product, result)
        updated += 1

    db.commit()
    return {
        "live_prices_enabled": True,
        "updated": updated,
        "skipped": len(products) - updated,
        "errors": errors,
    }


@app.post(
    "/prices/refresh/{product_id}",
    response_model=SinglePriceRefreshResponse,
)
def refresh_product_price(product_id: int, db: Session = Depends(get_db)) -> dict:
    product = db.get(ManualProduct, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="produto manual nao encontrado",
        )

    service = CreatorsApiPriceService()
    if not settings.can_fetch_live_prices or not service.is_configured():
        product.price_error = (
            "Preço real não consultado: integração oficial com Amazon ainda não "
            "configurada."
        )
        product.price_source = product.price_source or "none"
        db.commit()
        return {
            "product_id": product.id,
            "updated": False,
            "message": product.price_error,
        }

    try:
        result = service.fetch_price_by_asin(product.asin or "")
    except LivePriceUnavailableError as exc:
        product.price_error = str(exc)
        db.commit()
        return {
            "product_id": product.id,
            "updated": False,
            "message": str(exc),
        }

    _apply_live_price_result(product, result)
    db.commit()
    return {
        "product_id": product.id,
        "updated": True,
        "message": "Preço atualizado via integração oficial.",
    }


@app.get("/promotions", response_model=PromotionsRead)
def list_promotions(db: Session = Depends(get_db)) -> dict:
    items = _promotions_query(db).order_by(
        ManualProduct.discount_percent.desc().nullslast(),
        ManualProduct.title.asc(),
    ).all()
    message = ""
    if not items:
        message = (
            "Nenhuma promoção real verificada ainda. Configure a API oficial da "
            "Amazon e atualize os preços."
        )

    return {"items": items, "message": message}


@app.get("/exports/ready.json")
def export_ready_json(db: Session = Depends(get_db)) -> list[dict]:
    return [_product_export_row(product) for product in list_ready_manual_products(db)]


@app.get("/exports/ready.csv")
def export_ready_csv(db: Session = Depends(get_db)) -> Response:
    rows = [_product_export_row(product) for product in list_ready_manual_products(db)]
    fieldnames = [
        "id",
        "title",
        "author",
        "category",
        "subcategory",
        "template_type",
        "asin",
        "affiliate_link",
        "message",
        "notes",
        "current_price",
        "list_price",
        "currency",
        "discount_amount",
        "discount_percent",
        "availability",
        "deal_badge",
        "price_source",
        "last_price_checked_at",
        "price_error",
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ready-products.csv"'},
    )


def _top_books_categories(
    products: list[ManualProduct],
    max_per_category: int,
    mode: str,
) -> list[dict]:
    categories: dict[str, dict] = {}
    category_counts: dict[str, int] = {}

    for product in products:
        category = product.category or "sem_categoria"
        if category_counts.get(category, 0) >= max_per_category:
            continue

        if category not in categories:
            categories[category] = {
                "category": category,
                "label": _category_label(category),
                "items": [],
            }
            category_counts[category] = 0

        categories[category]["items"].append(_top_book_item(product, mode))
        category_counts[category] += 1

    return list(categories.values())


def _top_book_item(product: ManualProduct, mode: str) -> dict:
    if mode == "verified_promotions":
        return {
            "id": product.id,
            "title": product.title,
            "author": product.author,
            "asin": product.asin,
            "affiliate_link": product.affiliate_link,
            "status_label": "Promo\u00e7\u00e3o verificada",
            "price_label": _format_brl(product.current_price),
            "current_price": product.current_price,
            "list_price": product.list_price,
            "discount_percent": product.discount_percent,
            "last_price_checked_at": product.last_price_checked_at,
            "template_type": product.template_type,
            "priority": product.priority,
        }

    return {
        "id": product.id,
        "title": product.title,
        "author": product.author,
        "asin": product.asin,
        "affiliate_link": product.affiliate_link,
        "status_label": "Link pronto",
        "price_label": "Pre\u00e7o n\u00e3o verificado",
        "current_price": None,
        "list_price": None,
        "discount_percent": None,
        "last_price_checked_at": None,
        "template_type": product.template_type,
        "priority": product.priority,
    }


def _category_sort_key(category: str | None) -> tuple[int, str]:
    clean_category = category or ""
    try:
        return (TOP_CATEGORY_ORDER.index(clean_category), "")
    except ValueError:
        return (len(TOP_CATEGORY_ORDER), clean_category)


def _category_label(category: str) -> str:
    if category in TOP_CATEGORY_LABELS:
        return TOP_CATEGORY_LABELS[category]
    return category.replace("_", " ").capitalize()


def _format_brl(value: float | None) -> str:
    if value is None:
        return "Pre\u00e7o n\u00e3o verificado"
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _amazon_status_payload() -> dict:
    return {
        "source_mode": settings.amazon_source,
        "real_amazon_enabled": False,
        "has_associate_tag": settings.has_associate_tag,
        "has_creators_api_credentials": settings.has_creators_api_credentials,
        "can_fetch_live_prices": settings.can_fetch_live_prices,
        "can_detect_real_promotions": False,
        "message": (
            "A V1 atual usa lista fixa/manual. Preços reais ainda não estão "
            "sendo consultados na Amazon."
        ),
        "safe_mode": True,
    }


def _price_refresh_candidates(
    db: Session,
    only_ready: bool,
    limit: int,
) -> list[ManualProduct]:
    query = db.query(ManualProduct).filter(ManualProduct.active.is_(True))
    if only_ready:
        query = query.filter(
            ManualProduct.needs_asin.is_(False),
            ManualProduct.asin.isnot(None),
        )

    return query.order_by(ManualProduct.priority.asc(), ManualProduct.id.asc()).limit(limit).all()


def _promotions_query(db: Session):
    return db.query(ManualProduct).filter(
        ManualProduct.active.is_(True),
        ManualProduct.needs_asin.is_(False),
        ManualProduct.affiliate_link.isnot(None),
        ManualProduct.current_price.isnot(None),
        ManualProduct.last_price_checked_at.isnot(None),
        or_(
            ManualProduct.discount_percent > 0,
            ManualProduct.discount_amount > 0,
            ManualProduct.deal_badge.isnot(None) & (ManualProduct.deal_badge != ""),
        ),
    )


def _apply_live_price_result(product: ManualProduct, result) -> None:
    product.current_price = result.current_price
    product.list_price = result.list_price
    product.currency = result.currency or "BRL"
    product.discount_amount = result.discount_amount
    product.discount_percent = result.discount_percent
    product.availability = result.availability
    product.deal_badge = result.deal_badge
    product.price_source = result.source
    product.last_price_checked_at = result.checked_at
    product.price_error = None


def _product_export_row(product: ManualProduct) -> dict:
    return {
        "id": product.id,
        "title": product.title,
        "author": product.author,
        "category": product.category,
        "subcategory": product.subcategory,
        "template_type": product.template_type,
        "asin": product.asin,
        "affiliate_link": product.affiliate_link,
        "message": build_manual_product_message(product),
        "notes": product.notes,
        "current_price": product.current_price,
        "list_price": product.list_price,
        "currency": product.currency,
        "discount_amount": product.discount_amount,
        "discount_percent": product.discount_percent,
        "availability": product.availability,
        "deal_badge": product.deal_badge,
        "price_source": product.price_source,
        "last_price_checked_at": product.last_price_checked_at,
        "price_error": product.price_error,
    }


def _ensure_sqlite_price_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "manual_products" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("manual_products")
    }
    required_columns = {
        "current_price": "FLOAT",
        "list_price": "FLOAT",
        "currency": "VARCHAR(8) DEFAULT 'BRL'",
        "discount_amount": "FLOAT",
        "discount_percent": "FLOAT",
        "availability": "VARCHAR(120)",
        "deal_badge": "VARCHAR(120)",
        "price_source": "VARCHAR(40) DEFAULT 'none'",
        "last_price_checked_at": "DATETIME",
        "price_error": "TEXT",
    }

    with engine.begin() as connection:
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE manual_products ADD COLUMN {column_name} {column_type}")
                )


def _mask_associate_tag(tag: str) -> str:
    clean_tag = tag.strip() if tag else ""
    if not clean_tag:
        return "não configurada"

    if len(clean_tag) <= 6:
        return f"{clean_tag[:1]}***{clean_tag[-1:]}"

    return f"{clean_tag[:3]}***{clean_tag[-3:]}"
