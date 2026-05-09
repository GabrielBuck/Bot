from app.asin_utils import extract_asin_from_url, is_valid_asin


def test_extract_asin_from_dp_url() -> None:
    url = "https://www.amazon.com.br/algum-produto/dp/B09ZBKHN7P/ref=sr_1_1"

    assert extract_asin_from_url(url) == "B09ZBKHN7P"


def test_extract_asin_from_gp_product_url() -> None:
    url = "https://www.amazon.com.br/gp/product/B0D6T3QGHG"

    assert extract_asin_from_url(url) == "B0D6T3QGHG"


def test_validates_numeric_isbn_10() -> None:
    assert is_valid_asin("6555324511") is True
