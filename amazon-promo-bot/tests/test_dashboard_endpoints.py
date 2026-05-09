from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ManualProduct


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client, testing_session_local
    finally:
        app.dependency_overrides.clear()


def test_dashboard_summary_returns_200(client) -> None:
    test_client, _ = client

    response = test_client.get("/dashboard/summary")

    assert response.status_code == 200
    assert response.json()["total_products"] == 0


def test_dashboard_top_books_returns_200(client) -> None:
    test_client, _ = client

    response = test_client.get("/dashboard/top-books")

    assert response.status_code == 200


def test_dashboard_top_books_without_prices_returns_ready_links(client) -> None:
    test_client, testing_session_local = client
    _create_ready_product(testing_session_local, category="romantasia")

    response = test_client.get("/dashboard/top-books")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "ready_links"
    assert payload["has_verified_prices"] is False


def test_dashboard_top_books_without_prices_does_not_invent_price(client) -> None:
    test_client, testing_session_local = client
    _create_ready_product(testing_session_local, category="romantasia")

    response = test_client.get("/dashboard/top-books")

    payload = response.json()
    items = [
        item
        for category in payload["categories"]
        for item in category["items"]
    ]
    assert items
    assert all(item["current_price"] is None for item in items)
    assert all(item["price_label"] == "Preço não verificado" for item in items)


def test_dashboard_top_books_respects_max_per_category(client) -> None:
    test_client, testing_session_local = client
    _create_ready_product(
        testing_session_local,
        title="Livro A",
        category="romantasia",
        priority=1,
    )
    _create_ready_product(
        testing_session_local,
        title="Livro B",
        category="romantasia",
        priority=2,
    )
    _create_ready_product(
        testing_session_local,
        title="Livro C",
        category="romantasia",
        priority=3,
    )

    response = test_client.get("/dashboard/top-books?max_per_category=2")

    assert response.status_code == 200
    romantasia = response.json()["categories"][0]
    assert romantasia["category"] == "romantasia"
    assert len(romantasia["items"]) == 2


def test_dashboard_top_books_with_verified_discount_returns_promotions_mode(client) -> None:
    test_client, testing_session_local = client
    _create_ready_product(
        testing_session_local,
        category="romantasia",
        current_price=39.9,
        list_price=59.9,
        discount_percent=33,
        last_price_checked_at=datetime(2026, 4, 30, 10, 0),
    )

    response = test_client.get("/dashboard/top-books")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "verified_promotions"
    assert payload["has_verified_prices"] is True
    item = payload["categories"][0]["items"][0]
    assert item["current_price"] == 39.9
    assert item["discount_percent"] == 33


def test_dashboard_page_returns_200(client) -> None:
    test_client, _ = client

    response = test_client.get("/")

    assert response.status_code == 200
    assert "Amazon Promo Bot" in response.text


def test_docs_returns_200(client) -> None:
    test_client, _ = client

    response = test_client.get("/docs")

    assert response.status_code == 200


def test_dynamic_products_returns_empty_list_and_message(client) -> None:
    test_client, _ = client

    response = test_client.get("/dynamic-products")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert "não implementada" in response.json()["message"]


def test_amazon_integration_status_returns_safe_mode(client) -> None:
    test_client, _ = client

    response = test_client.get("/integrations/amazon/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["real_amazon_enabled"] is False
    assert payload["can_fetch_live_prices"] is False
    assert payload["can_detect_real_promotions"] is False
    assert payload["safe_mode"] is True


def test_price_refresh_without_api_does_not_create_fake_price(client) -> None:
    test_client, testing_session_local = client
    product_id = _create_ready_product(testing_session_local)

    response = test_client.post("/prices/refresh", json={"only_ready": True, "limit": 20})

    assert response.status_code == 200
    payload = response.json()
    assert payload["live_prices_enabled"] is False
    assert payload["updated"] == 0
    assert payload["skipped"] == 1

    db = testing_session_local()
    try:
        product = db.get(ManualProduct, product_id)
        assert product.current_price is None
        assert product.discount_percent is None
        assert product.price_error is not None
    finally:
        db.close()


def test_single_price_refresh_without_api_returns_controlled_message(client) -> None:
    test_client, testing_session_local = client
    product_id = _create_ready_product(testing_session_local)

    response = test_client.post(f"/prices/refresh/{product_id}")

    assert response.status_code == 200
    assert response.json()["updated"] is False


def test_promotions_without_real_price_returns_empty_items(client) -> None:
    test_client, testing_session_local = client
    _create_ready_product(testing_session_local)

    response = test_client.get("/promotions")

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_product_with_verified_discount_appears_in_promotions(client) -> None:
    test_client, testing_session_local = client
    _create_ready_product(
        testing_session_local,
        current_price=39.9,
        discount_percent=20,
        last_price_checked_at=datetime(2026, 4, 29, 10, 30),
    )

    response = test_client.get("/promotions")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_ready_product_without_price_does_not_appear_in_promotions(client) -> None:
    test_client, testing_session_local = client
    _create_ready_product(testing_session_local)

    response = test_client.get("/promotions")

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_export_ready_json_returns_200(client) -> None:
    test_client, _ = client

    response = test_client.get("/exports/ready.json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_export_ready_csv_returns_200_with_csv_content_type(client) -> None:
    test_client, _ = client

    response = test_client.get("/exports/ready.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")


def test_patch_manual_product_active_updates_active_flag(client) -> None:
    test_client, testing_session_local = client
    product_id = _create_ready_product(testing_session_local)

    response = test_client.patch(
        f"/manual-products/{product_id}/active",
        json={"active": False},
    )

    assert response.status_code == 200
    assert response.json()["active"] is False


def _create_ready_product(
    testing_session_local: sessionmaker[Session],
    title: str = "Produto pronto",
    category: str = "romance",
    priority: int = 3,
    current_price: float | None = None,
    list_price: float | None = None,
    discount_percent: float | None = None,
    last_price_checked_at: datetime | None = None,
) -> int:
    db = testing_session_local()
    try:
        product = ManualProduct(
            title=title,
            author="Autora",
            category=category,
            template_type="romance",
            format_preference="both",
            asin="B09ZBKHN7P",
            amazon_search_query=f"{title} Autora",
            affiliate_link="https://www.amazon.com.br/dp/B09ZBKHN7P?tag=tag-teste-20",
            search_link="https://www.amazon.com.br/s?k=Produto+pronto+Autora",
            needs_asin=False,
            active=True,
            priority=priority,
            current_price=current_price,
            list_price=list_price,
            discount_percent=discount_percent,
            last_price_checked_at=last_price_checked_at,
            price_source="creators_api" if current_price is not None else "none",
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product.id
    finally:
        db.close()
