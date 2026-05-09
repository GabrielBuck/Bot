from datetime import datetime

from app.messages import PENDING_ASIN_MESSAGE, build_manual_product_message
from app.models import ManualProduct


def test_message_for_product_without_asin_warns_pending_validation() -> None:
    product = ManualProduct(
        title="Quarta Asa",
        author="Rebecca Yarros",
        category="romantasia",
        template_type="romantasia",
        amazon_search_query="Quarta Asa Rebecca Yarros",
        needs_asin=True,
    )

    assert build_manual_product_message(product) == PENDING_ASIN_MESSAGE


def test_message_for_product_with_asin_contains_link_and_disclosure() -> None:
    product = ManualProduct(
        title="Powerless",
        author="Lauren Roberts",
        category="romantasia",
        template_type="romantasia",
        amazon_search_query="Powerless Lauren Roberts",
        asin="6555324511",
        affiliate_link="https://www.amazon.com.br/dp/6555324511?tag=minha-tag-20",
        needs_asin=False,
    )

    message = build_manual_product_message(product)

    assert "https://www.amazon.com.br/dp/6555324511?tag=minha-tag-20" in message
    assert "#pub" in message
    assert "#ComissõesPorCompra" in message


def test_message_without_verified_price_uses_check_link_text() -> None:
    product = ManualProduct(
        title="Powerless",
        author="Lauren Roberts",
        category="romantasia",
        template_type="romantasia",
        amazon_search_query="Powerless Lauren Roberts",
        asin="6555324511",
        affiliate_link="https://www.amazon.com.br/dp/6555324511?tag=minha-tag-20",
        needs_asin=False,
    )

    message = build_manual_product_message(product)

    assert "Preço: consultar no link" in message
    assert "Desconto verificado" not in message


def test_message_with_verified_price_includes_price_and_checked_at() -> None:
    product = ManualProduct(
        title="Powerless",
        author="Lauren Roberts",
        category="romantasia",
        template_type="romantasia",
        amazon_search_query="Powerless Lauren Roberts",
        asin="6555324511",
        affiliate_link="https://www.amazon.com.br/dp/6555324511?tag=minha-tag-20",
        needs_asin=False,
        current_price=39.9,
        discount_percent=20,
        last_price_checked_at=datetime(2026, 4, 29, 10, 30),
    )

    message = build_manual_product_message(product)

    assert "Preço verificado: R$ 39,90" in message
    assert "Verificado em: 29/04/2026 10:30" in message
    assert "Desconto verificado: 20%" in message
