from dataclasses import dataclass


@dataclass
class StockItem:
    name: str
    unit_id: int
    id: int | None = None


@dataclass
class StockBatch:
    stock_id: int
    price: float
    production_date: str
    expiration_date: str
    quantity: float
    status: str = 'available'
    added_at: str | None = None
    id: int | None = None


@dataclass
class RecipeItem:
    stock_id: int
    amount: float
    unit_id: int
    id: int | None = None


@dataclass
class Recipe:
    name: str
    price: float
    recipe_items: list[RecipeItem]
    id: int | None = None
