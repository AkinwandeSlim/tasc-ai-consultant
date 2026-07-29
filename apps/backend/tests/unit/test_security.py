"""Tests for security utilities."""

from app.core.security import constant_time_equal, sign_payload, verify_signature


class TestSigning:
    """Signature creation and verification tests."""

    def test_sign_and_verify(self) -> None:
        payload = b'{"hello": "world"}'
        secret = "test-secret"
        sig = sign_payload(payload, secret)
        assert sig.startswith("sha256=")
        assert verify_signature(payload, secret, sig)

    def test_wrong_secret_fails(self) -> None:
        payload = b'test'
        sig = sign_payload(payload, "secret-a")
        assert not verify_signature(payload, "secret-b", sig)

    def test_constant_time_equal(self) -> None:
        assert constant_time_equal("abc", "abc")
        assert not constant_time_equal("abc", "xyz")
