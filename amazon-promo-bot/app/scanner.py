from sqlalchemy.orm import Session

from .models import ManualProduct


def list_ready_manual_products(db: Session) -> list[ManualProduct]:
    return (
        db.query(ManualProduct)
        .filter(
            ManualProduct.active.is_(True),
            ManualProduct.needs_asin.is_(False),
            ManualProduct.affiliate_link.isnot(None),
        )
        .order_by(ManualProduct.priority.asc(), ManualProduct.title.asc())
        .all()
    )
