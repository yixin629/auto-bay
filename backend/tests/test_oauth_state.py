from app.core.security import create_oauth_state, decode_oauth_state


def test_oauth_state_roundtrip() -> None:
    payload = {"sub": "00000000-0000-0000-0000-000000000000", "platform": "douyin", "region": "CN"}
    token = create_oauth_state(payload)
    decoded = decode_oauth_state(token)

    assert decoded["sub"] == payload["sub"]
    assert decoded["platform"] == payload["platform"]
    assert decoded["region"] == payload["region"]
    assert decoded["type"] == "oauth_state"


def test_oauth_state_rejects_wrong_type() -> None:
    bad = create_oauth_state({"sub": "x", "platform": "douyin", "region": "CN", "type": "access"})
    decoded = decode_oauth_state(bad)
    assert decoded["type"] == "oauth_state"
