from app.core.security import decrypt_credentials, encrypt_credentials


def test_encrypt_decrypt_credentials_roundtrip() -> None:
    credentials = {
        "app_id": "abc",
        "app_secret": "secret",
        "access_token": "token",
    }

    encrypted = encrypt_credentials(credentials)

    assert "__encrypted__" in encrypted
    assert encrypted["__encrypted__"]
    assert decrypt_credentials(encrypted) == credentials


def test_decrypt_supports_legacy_plain_credentials() -> None:
    legacy = {"app_id": "legacy", "app_secret": "legacy-secret"}
    assert decrypt_credentials(legacy) == legacy


def test_decrypt_invalid_payload_returns_empty_dict() -> None:
    invalid = {"__encrypted__": "not-a-valid-token"}
    assert decrypt_credentials(invalid) == {}
