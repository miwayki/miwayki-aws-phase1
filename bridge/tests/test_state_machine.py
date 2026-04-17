"""Tests de la máquina de estados comerciales."""

from app.domain.state_machine import (
    validate_transition, can_transition, is_terminal, InvalidTransitionError,
)


def test_valid_new_to_quoted():
    validate_transition("new_inquiry", "quoted")


def test_valid_quoted_to_awaiting():
    validate_transition("quoted", "awaiting_payment")


def test_valid_requote():
    validate_transition("quoted", "quoted")


def test_invalid_new_to_closed_won():
    try:
        validate_transition("new_inquiry", "closed_won")
        assert False, "Should have raised"
    except InvalidTransitionError:
        pass


def test_invalid_terminal_exit():
    try:
        validate_transition("closed_won", "quoted")
        assert False, "Should have raised"
    except InvalidTransitionError:
        pass


def test_can_transition_true():
    assert can_transition("awaiting_payment", "voucher_received") is True


def test_can_transition_false():
    assert can_transition("new_inquiry", "voucher_received") is False


def test_is_terminal():
    assert is_terminal("closed_won") is True
    assert is_terminal("closed_lost") is True
    assert is_terminal("quoted") is False


# ── Run inline ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_valid_new_to_quoted()
    test_valid_quoted_to_awaiting()
    test_valid_requote()
    test_invalid_new_to_closed_won()
    test_invalid_terminal_exit()
    test_can_transition_true()
    test_can_transition_false()
    test_is_terminal()
    print("✅ All 8 state machine tests passed")
