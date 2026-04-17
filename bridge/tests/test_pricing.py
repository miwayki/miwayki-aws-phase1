"""Tests del motor de precios."""

from datetime import date
from decimal import Decimal
from app.domain.pricing import calculate_quote


def _tour(base=450):
    return {"code": "cusco-clasico", "name": "Cusco Clásico", "base_price_pen": base}


def test_base_price_simple():
    result = calculate_quote(
        tour=_tour(450), variant=None, travel_date=date(2026, 7, 15),
        party_size=4, group_type="individual",
        season=None, holiday=None, pricing_rules=[], exceptions=[],
    )
    assert result.base_total == Decimal("1800.00")
    assert result.total_price_pen == Decimal("1800.00")
    assert result.per_person_pen == Decimal("450.00")


def test_variant_adjustment():
    variant = {"code": "premium", "name": "Premium", "price_adjustment_pen": 100}
    result = calculate_quote(
        tour=_tour(450), variant=variant, travel_date=date(2026, 7, 15),
        party_size=2, group_type="individual",
        season=None, holiday=None, pricing_rules=[], exceptions=[],
    )
    assert result.base_price_per_person == Decimal("550.00")
    assert result.total_price_pen == Decimal("1100.00")


def test_season_alta():
    season = {"name": "Alta", "multiplier": 1.25, "active": True}
    result = calculate_quote(
        tour=_tour(400), variant=None, travel_date=date(2026, 7, 15),
        party_size=2, group_type="individual",
        season=season, holiday=None, pricing_rules=[], exceptions=[],
    )
    assert result.season_adjustment == Decimal("200.00")
    assert result.total_price_pen == Decimal("1000.00")


def test_holiday_surcharge_pct():
    holiday = {"name": "Fiestas Patrias", "surcharge_pct": 15, "active": True}
    result = calculate_quote(
        tour=_tour(400), variant=None, travel_date=date(2026, 7, 28),
        party_size=2, group_type="individual",
        season=None, holiday=holiday, pricing_rules=[], exceptions=[],
    )
    assert result.holiday_adjustment == Decimal("120.00")
    assert result.total_price_pen == Decimal("920.00")


def test_group_discount():
    rule = {
        "rule_type": "family_discount", "description": "Familia 4+pax",
        "group_type": "family", "min_pax": 4, "max_pax": None,
        "discount_pct": 10, "priority": 1, "active": True,
    }
    result = calculate_quote(
        tour=_tour(500), variant=None, travel_date=date(2026, 7, 15),
        party_size=4, group_type="family",
        season=None, holiday=None, pricing_rules=[rule], exceptions=[],
    )
    assert result.group_adjustment == Decimal("-200.00")
    assert result.total_price_pen == Decimal("1800.00")


def test_exception_override():
    exc = {"description": "Promo verano", "flat_price_pen": 300, "active": True}
    result = calculate_quote(
        tour=_tour(500), variant=None, travel_date=date(2026, 7, 15),
        party_size=4, group_type="individual",
        season=None, holiday=None, pricing_rules=[], exceptions=[exc],
    )
    assert result.is_override is True
    assert result.total_price_pen == Decimal("1200.00")
    assert result.per_person_pen == Decimal("300.00")


def test_total_never_negative():
    rule = {
        "rule_type": "mega_discount", "description": "Test",
        "group_type": "any", "min_pax": None, "max_pax": None,
        "discount_pct": 200, "priority": 1, "active": True,
    }
    result = calculate_quote(
        tour=_tour(100), variant=None, travel_date=date(2026, 7, 15),
        party_size=1, group_type="individual",
        season=None, holiday=None, pricing_rules=[rule], exceptions=[],
    )
    assert result.total_price_pen == Decimal("0.00")


def test_combined_season_holiday_group():
    season = {"name": "Alta", "multiplier": 1.20, "active": True}
    holiday = {"name": "Semana Santa", "surcharge_pct": 10, "active": True}
    rule = {
        "description": "Grupo 6+", "group_type": "any", "min_pax": 6,
        "max_pax": None, "discount_pct": 5, "priority": 1, "active": True,
    }
    result = calculate_quote(
        tour=_tour(400), variant=None, travel_date=date(2026, 4, 17),
        party_size=6, group_type="family",
        season=season, holiday=holiday, pricing_rules=[rule], exceptions=[],
    )
    # base = 400 * 6 = 2400
    assert result.season_adjustment == Decimal("480.00")   # +20%
    assert result.holiday_adjustment == Decimal("240.00")   # +10%
    assert result.group_adjustment == Decimal("-120.00")    # -5%
    assert result.total_price_pen == Decimal("3000.00")


# ── Run inline ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_base_price_simple()
    test_variant_adjustment()
    test_season_alta()
    test_holiday_surcharge_pct()
    test_group_discount()
    test_exception_override()
    test_total_never_negative()
    test_combined_season_holiday_group()
    print("✅ All 8 pricing tests passed")
