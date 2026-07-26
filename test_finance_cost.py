"""Self-check for the finance cost math. Run: python test_finance_cost.py"""

from models.entities import BatchConsumption
from models.finance_model import total_cost


def c(amount, unit_price):
    return BatchConsumption(stock_batch_id=1, stock_id=1,
                            amount=amount, unit_price=unit_price)


if __name__ == "__main__":
    assert total_cost([]) == 0

    # FIFO across two batches at different prices: 3*2.0 + 1.5*4.0
    assert total_cost([c(3, 2.0), c(1.5, 4.0)]) == 12.0

    # fractional amounts (grams converted from kg) stay within float tolerance
    assert abs(total_cost([c(0.1, 3.0)] * 3) - 0.9) < 1e-9

    print("finance cost math OK")
