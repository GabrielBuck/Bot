from datetime import datetime

from .models import ManualProduct


PENDING_ASIN_MESSAGE = (
    "Produto ainda precisa de ASIN/link validado antes de gerar mensagem pública."
)


def build_manual_product_message(product: ManualProduct) -> str:
    if product.needs_asin or not product.affiliate_link:
        return PENDING_ASIN_MESSAGE

    title = product.title
    author_line = f"por {product.author}" if product.author else ""
    affiliate_link = product.affiliate_link
    normalized_template = (product.template_type or "padrao").strip().casefold()
    price_block = _build_price_block(product)

    if normalized_template in {"livros", "romantasia"}:
        intro = "📚 Achado literário na Amazon!"
        description = (
            "Para quem curte romance, fantasia, romantasia ou livros que aparecem "
            "muito no BookTok."
        )
    elif normalized_template == "dark_romance":
        intro = "🖤 Achado de dark romance na Amazon!"
        description = (
            "Indicação para leitoras que curtem romance intenso, dramático e com "
            "clima mais sombrio. Verifique a classificação indicativa e os gatilhos "
            "antes da leitura."
        )
    elif normalized_template == "kindle":
        intro = "📱 Achado para Kindle!"
        description = (
            "Boa opção para quem lê no Kindle ou quer acompanhar achados de eBook."
        )
    elif normalized_template == "thriller":
        intro = "🔎 Achado de suspense/thriller na Amazon!"
        description = "Para quem gosta de mistério, plot twist e leitura viciante."
    elif normalized_template == "romance":
        intro = "💕 Achado de romance na Amazon!"
        description = (
            "Para quem quer uma leitura envolvente, romântica e com cara de BookTok."
        )
    else:
        intro = "📚 Achado literário na Amazon!"
        description = "Para quem curte livros e quer acompanhar achados na Amazon."

    official_price_notice = ""
    if _has_verified_price(product):
        official_price_notice = (
            "\nInformações de preço e disponibilidade são precisas no horário "
            "indicado e podem mudar. O preço exibido na Amazon no momento da "
            "compra é o válido."
        )

    return f"""{intro}

{title}
{author_line}

{description}

{price_block}

🔗 {affiliate_link}

Preço e disponibilidade podem mudar a qualquer momento.{official_price_notice}

#pub #ComissõesPorCompra
Como associado da Amazon, recebo por compras qualificadas."""


def _build_price_block(product: ManualProduct) -> str:
    if not _has_verified_price(product):
        return "💰 Preço: consultar no link"

    lines = [
        f"💰 Preço verificado: {_format_brl(product.current_price)}",
        f"🕒 Verificado em: {_format_datetime(product.last_price_checked_at)}",
    ]

    if product.discount_percent and product.discount_percent > 0:
        lines.append(f"🔥 Desconto verificado: {product.discount_percent:g}%")

    return "\n".join(lines)


def _has_verified_price(product: ManualProduct) -> bool:
    return bool(product.current_price is not None and product.last_price_checked_at)


def _format_brl(value: float | None) -> str:
    if value is None:
        return "R$ 0,00"

    return f"R$ {value:.2f}".replace(".", ",")


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return ""

    return value.strftime("%d/%m/%Y %H:%M")
