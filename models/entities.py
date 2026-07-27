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


@dataclass
class OrderItem:
    recipe_id: int
    recipe_name: str
    quantity: int


@dataclass
class Order:
    items: list[OrderItem]
    id: int | None = None
    created_at: str | None = None
    status: str = 'draft'
    subtotal: float = 0.0
    cost: float = 0.0


@dataclass
class BatchConsumption:
    """One batch touched by an order's FIFO deduction — the hand-off from
    OrderModel to FinanceModel, which prices it and writes orders.cost."""
    stock_batch_id: int
    stock_id: int
    amount: float
    unit_price: float


@dataclass
class Shortage:
    stock_id: int
    stock_name: str
    required: float
    available: float
    unit: str


@dataclass
class ValidationResult:
    ok: bool
    shortages: list[Shortage]
    errors: list[str]
    subtotal: float = 0.0
