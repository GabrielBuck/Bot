import re


ASIN_PATTERN = re.compile(r"/(?:dp|gp/product)/([A-Za-z0-9]{10})(?:[/?#]|$)")


def is_valid_asin(value: str) -> bool:
    clean_value = value.strip() if value else ""
    if len(clean_value) != 10:
        return False

    if not clean_value.isalnum():
        return False

    upper_value = clean_value.upper()
    return upper_value.startswith("B0") or clean_value.isdigit()


def extract_asin_from_url(url: str) -> str | None:
    clean_url = url.strip() if url else ""
    if not clean_url:
        return None

    match = ASIN_PATTERN.search(clean_url)
    if not match:
        return None

    candidate = match.group(1)
    if not is_valid_asin(candidate):
        return None

    return candidate.upper()
