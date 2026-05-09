from urllib.parse import urlencode


def build_affiliate_link(asin: str, associate_tag: str) -> str:
    clean_asin = asin.strip() if asin else ""
    clean_tag = associate_tag.strip() if associate_tag else ""

    if not clean_asin:
        raise ValueError("ASIN é obrigatório para link direto de afiliado")

    if not clean_tag:
        raise ValueError("Associate tag é obrigatória")

    return f"https://www.amazon.com.br/dp/{clean_asin}?tag={clean_tag}"


def build_amazon_search_link(query: str, associate_tag: str | None = None) -> str:
    clean_query = query.strip() if query else ""
    if not clean_query:
        raise ValueError("Query de busca é obrigatória")

    params = {"k": clean_query}
    clean_tag = associate_tag.strip() if associate_tag else ""
    if clean_tag:
        params["tag"] = clean_tag

    return f"https://www.amazon.com.br/s?{urlencode(params)}"
