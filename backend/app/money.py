"""Money as integer cents. Parsing goes through Decimal; floats are never used for arithmetic."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


def to_cents(raw) -> int | None:
    """Accept Reap amount shapes: "72.90", 72.9, 129, {"amount": "72.90", ...}, {"amount": {"amount": ...}}."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        return to_cents(raw.get("amount"))
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        raise ValueError(f"not a money value: {raw!r}")
    try:
        d = Decimal(str(raw).strip())
    except InvalidOperation as e:
        raise ValueError(f"not a money value: {raw!r}") from e
    if not d.is_finite():
        raise ValueError(f"not a money value: {raw!r}")
    if isinstance(raw, str) and d.as_tuple().exponent < -2:
        raise ValueError(f"more than two decimals: {raw!r}")
    return int((d.quantize(CENT, rounding=ROUND_HALF_UP) * 100).to_integral_value())


def fmt(cents: int) -> str:
    return f"{Decimal(cents) / 100:.2f}"
