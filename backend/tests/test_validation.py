"""Tests for password and input validation helpers."""

import pytest
from app.validation import validate_password_strength


def test_strong_password_passes():
    validate_password_strength("Str0ngPass!")


@pytest.mark.parametrize("pw,fragment", [
    ("short1A", "8 characters"),
    ("alllowercase1", "uppercase"),
    ("ALLUPPERCASE1", "lowercase"),
    ("NoDigitsHere", "digit"),
])
def test_weak_passwords_rejected(pw, fragment):
    with pytest.raises(ValueError, match=fragment):
        validate_password_strength(pw)
