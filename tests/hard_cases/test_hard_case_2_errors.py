"""Hard Case 2: 429 response with reset time, expired token, content rejected."""

import pytest
import httpx
from connectors.discourse.errors import map_discourse_error
from core.errors import ErrorCode


def test_hard_case_2_error_mapping():
    # 1. 429 Rate Limit with reset time
    req = httpx.Request("POST", "https://forum.incubrix.test/posts.json")
    resp_429 = httpx.Response(status_code=429, headers={"Retry-After": "45"}, text='{"errors":["Rate limited"]}', request=req)
    err_429 = map_discourse_error(httpx.HTTPStatusError("Rate limited", request=req, response=resp_429))
    assert err_429.code == ErrorCode.PLATFORM_RATE_LIMIT
    assert err_429.retryable is True
    assert err_429.details["reset_seconds"] == 45

    # 2. Expired / Invalid Token (401/403)
    resp_401 = httpx.Response(status_code=401, text='{"errors":["Invalid token"]}', request=req)
    err_401 = map_discourse_error(httpx.HTTPStatusError("Auth error", request=req, response=resp_401))
    assert err_401.code == ErrorCode.CONNECTION_AUTH_EXPIRED
    assert err_401.retryable is False

    # 3. Content Rejected (422)
    resp_422 = httpx.Response(status_code=422, text='{"errors":["Body too similar to previous post"]}', request=req)
    err_422 = map_discourse_error(httpx.HTTPStatusError("Rejected", request=req, response=resp_422))
    assert err_422.code == ErrorCode.PLATFORM_CONTENT_REJECTED
    assert err_422.retryable is False
    assert "Body too similar" in err_422.message
