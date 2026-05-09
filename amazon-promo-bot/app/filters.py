from .models import ManualProduct


def manual_product_is_ready(product: ManualProduct) -> bool:
    return bool(product.active and not product.needs_asin and product.affiliate_link)
