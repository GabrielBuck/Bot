import pytest

from app.affiliate import build_affiliate_link


def test_build_affiliate_link_with_tag() -> None:
    link = build_affiliate_link("B09ZBKHN7P", "minha-tag-20")

    assert link == "https://www.amazon.com.br/dp/B09ZBKHN7P?tag=minha-tag-20"


def test_build_affiliate_link_rejects_empty_asin() -> None:
    with pytest.raises(ValueError):
        build_affiliate_link("", "minha-tag-20")


def test_build_affiliate_link_rejects_empty_tag() -> None:
    with pytest.raises(ValueError):
        build_affiliate_link("B09ZBKHN7P", "")
