"""Constitution V: money is whole cents, parsed with Decimal, never float arithmetic."""
import pytest

from app.money import fmt, to_cents


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("72.90", 7290),
        ("72.9", 7290),
        ("0.10", 10),
        ("150", 15000),
        (72.9, 7290),  # float input from JSON is accepted but converted via str -> Decimal
        (129, 12900),
        ({"amount": "72.90", "currency": "SGD"}, 7290),
        ({"amount": {"amount": "5.00", "currency": "SGD"}}, 500),
        ({"amount": 5.5}, 550),
    ],
)
def test_to_cents_parses_reap_amount_shapes(raw, expected):
    assert to_cents(raw) == expected


def test_to_cents_none_and_missing_amount_return_none():
    assert to_cents(None) is None
    assert to_cents({}) is None
    assert to_cents({"amount": None}) is None


def test_to_cents_avoids_binary_float_rounding_errors():
    assert to_cents(0.1 + 0.2) == 30
    assert to_cents(1.005) == 101  # float input rounds half-up, not banker's


@pytest.mark.parametrize("bad", ["abc", "NaN", "inf", "", [1], object()])
def test_to_cents_rejects_non_numeric(bad):
    with pytest.raises(ValueError):
        to_cents(bad)


def test_to_cents_rejects_more_than_two_decimals():
    with pytest.raises(ValueError):
        to_cents("1.234")


@pytest.mark.parametrize("cents,text", [(7290, "72.90"), (0, "0.00"), (5, "0.05"), (15000, "150.00")])
def test_fmt_formats_cents_with_two_decimals(cents, text):
    assert fmt(cents) == text
