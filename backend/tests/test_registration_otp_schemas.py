from pydantic import ValidationError
import pytest
from app.schemas import RegisterStartIn, RegisterVerifyIn, LoginIn

def test_registration_normalizes_indian_ten_digit_phone():
    data = RegisterStartIn(name="Test Driver", email="driver@example.com", phone="9876543210", password="secure-pass-123")
    assert data.phone == "+919876543210"

def test_registration_preserves_international_phone():
    data = RegisterStartIn(name="Test Driver", email="driver@example.com", phone="+44 7700 900123", password="secure-pass-123")
    assert data.phone == "+447700900123"

def test_registration_rejects_short_phone():
    with pytest.raises(ValidationError):
        RegisterStartIn(name="Test Driver", email="driver@example.com", phone="12345", password="secure-pass-123")

def test_otp_requires_six_digits():
    with pytest.raises(ValidationError):
        RegisterVerifyIn(challenge_id="challenge", otp="123")

def test_login_identifier_accepts_name_phone_or_email_as_text():
    assert LoginIn(identifier="9876543210", password="secret").identifier == "9876543210"
    assert LoginIn(identifier="driver@example.com", password="secret").identifier == "driver@example.com"
