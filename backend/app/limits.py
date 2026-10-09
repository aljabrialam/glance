"""Per-purchase limit rule. Pure, whole cents, inclusive at the limit (constitution III, V, VII)."""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LimitDecision:
    limit_cents: int
    total_cents: int
    allowed: bool
    over_by_cents: int
    remaining_cents: int

    def to_dict(self) -> dict:
        d = asdict(self)
        return {
            "limitCents": d["limit_cents"],
            "totalCents": d["total_cents"],
            "allowed": d["allowed"],
            "overByCents": d["over_by_cents"],
            "remainingCents": d["remaining_cents"],
        }


def _int(name: str, v) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise TypeError(f"{name} must be int cents, got {type(v).__name__}")
    return v


def evaluate(total_cents: int, limit_cents: int) -> LimitDecision:
    total = _int("total_cents", total_cents)
    limit = _int("limit_cents", limit_cents)
    if limit <= 0:
        raise ValueError("limit_cents must be positive")
    if total < 0:
        raise ValueError("total_cents must not be negative")
    over = max(0, total - limit)
    return LimitDecision(
        limit_cents=limit,
        total_cents=total,
        allowed=over == 0,
        over_by_cents=over,
        remaining_cents=max(0, limit - total),
    )
