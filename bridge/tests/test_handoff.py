"""Tests de handoff evaluator."""

from datetime import date, timedelta

from app.domain.handoff import evaluate_handoff


def test_large_group_triggers_handoff():
    result = evaluate_handoff(party_size=20)
    assert result.required is True
    assert "excede" in result.reason


def test_school_group_triggers_handoff():
    result = evaluate_handoff(group_type="school")
    assert result.required is True
    assert "escolar" in result.reason


def test_tour_not_found_triggers_handoff():
    result = evaluate_handoff(tour_found=False)
    assert result.required is True
    assert "no encontrada" in result.reason


def test_voucher_always_triggers_handoff():
    result = evaluate_handoff(is_voucher=True)
    assert result.required is True
    assert "Voucher" in result.reason


def test_far_future_triggers_handoff():
    future = date.today() + timedelta(days=900)
    result = evaluate_handoff(travel_date=future)
    assert result.required is True
    assert "rango operativo" in result.reason


def test_high_score_triggers_handoff():
    result = evaluate_handoff(lead_score=75)
    assert result.required is True
    assert "score" in result.reason.lower()


def test_normal_does_not_trigger():
    result = evaluate_handoff(
        party_size=4, group_type="family", tour_found=True,
        travel_date=date.today() + timedelta(days=30),
    )
    assert result.required is False


def test_small_group_no_handoff():
    result = evaluate_handoff(party_size=2, group_type="individual")
    assert result.required is False


# ── Run inline ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_large_group_triggers_handoff()
    test_school_group_triggers_handoff()
    test_tour_not_found_triggers_handoff()
    test_voucher_always_triggers_handoff()
    test_far_future_triggers_handoff()
    test_high_score_triggers_handoff()
    test_normal_does_not_trigger()
    test_small_group_no_handoff()
    print("✅ All 8 handoff tests passed")
