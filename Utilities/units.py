"""Unit conversion helpers for the order flow.

The `units` table (kg, mL, L, g) stores no conversion factors, and the units span
two physical dimensions (mass vs. volume), so a static map is used. Conversion is
only valid within the same dimension — a cross-dimension request (e.g. g -> L) is a
data error and raises ValueError so the caller can fail loudly rather than silently
mis-compare stock.
"""

# name -> (dimension, factor_to_base_unit)
# base unit is grams for mass, millilitres for volume.
UNIT_FACTORS = {
    'g':  ('mass', 1.0),
    'kg': ('mass', 1000.0),
    'mL': ('volume', 1.0),
    'L':  ('volume', 1000.0),
}


def convert(amount: float, from_unit: str, to_unit: str) -> float:
    """Convert `amount` from `from_unit` to `to_unit`.

    Raises ValueError on an unknown unit or a cross-dimension conversion.
    """
    if from_unit not in UNIT_FACTORS:
        raise ValueError(f"Unknown unit '{from_unit}'")
    if to_unit not in UNIT_FACTORS:
        raise ValueError(f"Unknown unit '{to_unit}'")

    from_dim, from_factor = UNIT_FACTORS[from_unit]
    to_dim, to_factor = UNIT_FACTORS[to_unit]

    if from_dim != to_dim:
        raise ValueError(
            f"Cannot convert '{from_unit}' ({from_dim}) to "
            f"'{to_unit}' ({to_dim}) — incompatible dimensions"
        )

    return amount * from_factor / to_factor
