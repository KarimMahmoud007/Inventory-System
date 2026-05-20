from datetime import datetime
from models.entities import StockItem, StockBatch


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
