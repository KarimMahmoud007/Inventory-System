from dataclasses import dataclass


@dataclass
class StockItem:
    name: str
    unit_id: int
    price: float
    production_date: str
    expiration_date: str
    quantity: float
