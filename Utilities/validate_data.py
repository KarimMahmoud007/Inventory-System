from datetime import datetime
from models.entities import StockItem

def validate_data(item: StockItem) -> bool:
    try:
        name = item.name.strip()
        unit = item.unit_id
        price = float(item.price)
        prod = datetime.strptime(item.production_date, "%Y-%m-%d") if item.production_date else None
        exp = datetime.strptime(item.expiration_date, "%Y-%m-%d")
        qty = float(item.quantity)

        if name and unit >= 1 and price >= 0 and prod is not None and prod < exp and qty >= 0:
            return True
        return False

    except (ValueError, TypeError):
        return False


def validate_recipe_item(amount: float) -> bool:
    try:
        return amount > 0
    except (ValueError, TypeError):
        return False