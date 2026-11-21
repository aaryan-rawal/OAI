from app.config import settings
from app.services.integrations.sms import configured


def test_twilio_requires_all_credentials(monkeypatch):
    monkeypatch.setattr(settings, "SMS_PROVIDER", "twilio")
    monkeypatch.setattr(settings, "SMS_TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setattr(settings, "SMS_TWILIO_AUTH_TOKEN", "secret")
    monkeypatch.setattr(settings, "SMS_TWILIO_MESSAGING_SERVICE_SID", "MG123")
    monkeypatch.setattr(settings, "SMS_SENDER_ID", "")
    assert configured() is True
    monkeypatch.setattr(settings, "SMS_TWILIO_AUTH_TOKEN", "")
    assert configured() is False


def test_generic_sms_requires_endpoint_key_and_sender(monkeypatch):
    monkeypatch.setattr(settings, "SMS_PROVIDER", "generic")
    monkeypatch.setattr(settings, "SMS_API_BASE_URL", "https://sms.example.test")
    monkeypatch.setattr(settings, "SMS_API_KEY", "key")
    monkeypatch.setattr(settings, "SMS_SENDER_ID", "OPTIFREIGHT")
    assert configured() is True
    monkeypatch.setattr(settings, "SMS_API_BASE_URL", "")
    assert configured() is False
