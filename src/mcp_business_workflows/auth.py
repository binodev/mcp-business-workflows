import hmac

from mcp_business_workflows.logging import get_logger

log = get_logger(__name__)


class AuthError(Exception):
    pass


def verify_token(provided: str, expected: str) -> None:
    """Constant-time comparison to prevent timing attacks."""
    if not hmac.compare_digest(provided.encode(), expected.encode()):
        log.warning("auth.invalid_token")
        raise AuthError("Invalid or missing API token")


def bearer_from_header(authorization: str) -> str:
    """Extract token from 'Authorization: Bearer <token>' header."""
    if not authorization.startswith("Bearer "):
        raise AuthError("Authorization header must use Bearer scheme")
    return authorization.removeprefix("Bearer ").strip()
