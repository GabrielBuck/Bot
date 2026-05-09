import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.manual_catalog import import_seed_products, load_seed_products
from app.models import ManualProduct


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()


def test_load_seed_products_returns_catalog() -> None:
    products = load_seed_products()

    assert len(products) > 100
    assert any(product["title"] == "Quarta Asa" for product in products)


def test_import_seed_products_does_not_duplicate(db_session: Session) -> None:
    first_summary = import_seed_products(db_session)
    second_summary = import_seed_products(db_session)

    assert first_summary["inserted"] == first_summary["total_seed"]
    assert second_summary["inserted"] == 0
    assert second_summary["skipped"] == second_summary["total_seed"]


def test_product_without_asin_stays_pending(db_session: Session) -> None:
    import_seed_products(db_session)

    product = (
        db_session.query(ManualProduct)
        .filter(ManualProduct.title == "Quarta Asa")
        .one()
    )

    assert product.needs_asin is True
    assert product.affiliate_link is None
    assert product.search_link is not None


def test_product_with_asin_is_ready_for_manual_message(db_session: Session) -> None:
    import_seed_products(db_session)

    product = (
        db_session.query(ManualProduct)
        .filter(ManualProduct.title == "Powerless")
        .one()
    )

    assert product.needs_asin is False
    assert product.asin == "6555324511"
    assert product.affiliate_link == "https://www.amazon.com.br/dp/6555324511?tag=tag-teste-20"
