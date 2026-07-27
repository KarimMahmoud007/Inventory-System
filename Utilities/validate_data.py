from datetime import datetime
from models.entities import StockItem, StockBatch


def parse_float(text: str, field_name: str) -> tuple[float | None, str | None]:
    """Parse a raw form field into a float. Returns (value, error); error is None
    on success.

    Forms must call this BEFORE constructing an entity — the dataclass validators
    below run on an already-built entity, so they cannot protect the float()
    conversion that builds it.
    """
    try:
        return float(text), None
    except (ValueError, TypeError):
        return None, f"{field_name} must be a number."


def validate_stock_item(item: StockItem) -> bool:
    try:
        name = item.name.strip()
        unit = item.unit_id
        return bool(name) and unit >= 1
    except (ValueError, TypeError, AttributeError):
        return False


def validate_stock_batch(batch: StockBatch) -> bool:
    try:
        price = float(batch.price)
        prod = datetime.strptime(batch.production_date, "%Y-%m-%d") if batch.production_date else None
        exp = datetime.strptime(batch.expiration_date, "%Y-%m-%d")
        qty = float(batch.quantity)
        return price >= 0 and prod is not None and exp > prod and qty > 0
    except (ValueError, TypeError):
        return False


def validate_recipe_item(amount: float) -> bool:
    try:
        return amount > 0
    except (ValueError, TypeError):
        return False
