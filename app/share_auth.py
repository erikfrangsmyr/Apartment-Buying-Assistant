"""Optional share token for LAN / tailnet access to the web UI and static assets."""

import os
import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

SHARE_TOKEN_ENV_KEYS = ("SHARE_TOKEN", "APP_SHARE_TOKEN")
SHARE_COOKIE_NAME = "aba_share"
SHARE_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

TOKEN_HINT_HTML = """<!DOCTYPE html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bostadsköp — länk krävs</title>
</head>
<body style="font-family: system-ui, sans-serif; max-width: 32rem; margin: 3rem auto; padding: 0 1rem;">
  <h1>Kan inte öppna appen</h1>
  <p>Be Erik om länken med token.</p>
</body>
</html>"""


def get_share_token() -> str | None:
    for key in SHARE_TOKEN_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            return value
    return None


def resolve_share_token(request: Request) -> str | None:
    override = getattr(request.app.state, "share_token_override", None)
    if override:
        return override
    return get_share_token()


def _token_from_request(request: Request) -> str | None:
    query = request.query_params.get("token")
    if query:
        return query
    header = request.headers.get("X-Share-Token")
    if header:
        return header
    return None


def _is_protected_path(path: str) -> bool:
    if path in ("/", "/ui"):
        return True
    return path == "/app" or path.startswith("/app/") or path.startswith("/static/")


def _is_excluded_path(path: str) -> bool:
    if path == "/health":
        return True
    if path == "/docs" or path.startswith("/docs/"):
        return True
    if path == "/openapi.json" or path.startswith("/redoc"):
        return True
    return False


def tokens_match(expected: str, provided: str | None) -> bool:
    if provided is None:
        return False
    return secrets.compare_digest(expected.encode("utf-8"), provided.encode("utf-8"))


class ShareAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        expected = resolve_share_token(request)
        if not expected or _is_excluded_path(request.url.path):
            return await call_next(request)

        if not _is_protected_path(request.url.path):
            return await call_next(request)

        provided = _token_from_request(request)
        cookie = request.cookies.get(SHARE_COOKIE_NAME)
        authorized = tokens_match(expected, provided) or tokens_match(expected, cookie)

        if not authorized:
            accept = request.headers.get("accept", "")
            if (
                request.url.path.startswith("/app")
                or request.url.path == "/"
            ) and "text/html" in accept:
                return HTMLResponse(TOKEN_HINT_HTML, status_code=403)
            return Response(status_code=403)

        response = await call_next(request)
        if tokens_match(expected, provided) and not tokens_match(expected, cookie):
            response.set_cookie(
                SHARE_COOKIE_NAME,
                expected,
                httponly=True,
                samesite="lax",
                max_age=SHARE_COOKIE_MAX_AGE,
                path="/",
            )
        return response
