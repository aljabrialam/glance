"""AC-001-07 [api]: the per-purchase limit rule is a pure function over whole cents."""
import pytest

from app.limits import LimitDecision, evaluate


def test_AC_001_07_under_limit_is_allowed_with_remaining():
    d = evaluate(total_cents=13400, limit_cents=15000)
    assert d == LimitDecision(limit_cents=15000, total_cents=13400, allowed=True, over_by_cents=0, remaining_cents=1600)


def test_AC_001_07_equal_to_limit_is_allowed_inclusive():
    d = evaluate(total_cents=15000, limit_cents=15000)
    assert d.allowed is True
    assert d.over_by_cents == 0
    assert d.remaining_cents == 0


def test_AC_001_07_over_limit_is_blocked_with_exact_over_by():
    d = evaluate(total_cents=15701, limit_cents=15000)
    assert d.allowed is False
    assert d.over_by_cents == 701
    assert d.remaining_cents == 0


def test_AC_001_07_one_cent_over_is_blocked():
    assert evaluate(15001, 15000).allowed is False


@pytest.mark.parametrize("bad", [-1, 0])
def test_AC_001_07_non_positive_limit_is_rejected(bad):
    with pytest.raises(ValueError):
        evaluate(100, bad)


def test_AC_001_07_negative_total_is_rejected():
    with pytest.raises(ValueError):
        evaluate(-1, 15000)


@pytest.mark.parametrize("total,limit", [(1.0, 15000), (100, 150.0), ("100", 15000)])
def test_AC_001_07_only_integers_are_accepted_no_floats_for_money(total, limit):
    with pytest.raises(TypeError):
        evaluate(total, limit)  # type: ignore[arg-type]


def test_AC_001_07_decision_serialises_to_api_shape():
    assert evaluate(13400, 15000).to_dict() == {
        "limitCents": 15000,
        "totalCents": 13400,
        "allowed": True,
        "overByCents": 0,
        "remainingCents": 1600,
    }
