"""B2C sign-in adapter tests: synthetic responses, no real credentials or network."""

import json
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

import aiohttp
import pytest
from yarl import URL

from custom_components.flame_connect.adapters.cloud.auth import create_transaction
from custom_components.flame_connect.adapters.cloud.credential_login import (
    BASE,
    ORIGIN,
    CredentialLogin,
    follow,
    login_fields,
    request,
    trusted_url,
)
from custom_components.flame_connect.domain.errors import AuthenticationError, ConnectionError, ProtocolError


class Response:
    def __init__(self, status=200, body="", location=""):
        self.status = status
        self.body = body.encode()
        self.headers = {"Location": location}
        self.content = self

    async def iter_chunked(self, size):
        yield self.body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class Session:
    def __init__(self, responses):
        self.request = Mock(side_effect=responses)
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True


PAGE = json.dumps({"csrf": "csrf+/=", "transId": "StateProperties=tx+/="})


async def test_login_headers_redirects_and_isolated_cookie_jar(caplog):
    transaction = create_transaction()
    callback = transaction.settings.redirect_uri + "?code=fake-code&state=" + transaction.state
    session = Session(
        [
            Response(302, location="/login"),
            Response(body=PAGE),
            Response(body='{"status":"200"}'),
            Response(302, location="/continue"),
            Response(302, location=callback),
        ]
    )
    with patch(
        "custom_components.flame_connect.adapters.cloud.credential_login.aiohttp.ClientSession", return_value=session
    ) as factory:
        result = await CredentialLogin().authorize(transaction, "test@example.invalid", "fake-password")
    assert transaction.consume(result) == "fake-code"
    assert session.closed
    calls = session.request.call_args_list
    post = next(call for call in calls if call.args[0] == "POST")
    assert post.args[1].startswith(BASE + "SelfAsserted?")
    assert post.kwargs["headers"]["Origin"] == ORIGIN
    assert post.kwargs["headers"]["Referer"] == ORIGIN + "/login"
    assert post.kwargs["headers"]["X-CSRF-TOKEN"] == "csrf+/="
    assert post.kwargs["headers"]["X-Requested-With"] == "XMLHttpRequest"
    assert post.kwargs["data"] == {
        "request_type": "RESPONSE",
        "email": "test@example.invalid",
        "password": "fake-password",
    }
    query = parse_qs(urlsplit(calls[3].args[1]).query)
    assert query["csrf_token"] == ["csrf+/="]
    assert query["tx"] == ["StateProperties=tx+/="]
    assert all(call.kwargs["allow_redirects"] is False and trusted_url(call.args[1]) for call in calls)
    jar = factory.call_args.kwargs["cookie_jar"]
    jar.update_cookies({"x-ms-cpim-csrf": "cookie+/="}, URL(ORIGIN))
    assert jar.filter_cookies(URL(ORIGIN)).output(header="").strip() == "x-ms-cpim-csrf=cookie+/="
    for secret in ("fake-password", "csrf+/=", "fake-code", "cookie+/="):
        assert secret not in caplog.text


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.invalid/",
        "http://gdhvb2cflameconnect.b2clogin.com/",
        ORIGIN + ":443/",
        ORIGIN + ":bad/",
        "https://user@gdhvb2cflameconnect.b2clogin.com/",
        ORIGIN + "/#fragment",
    ],
)
async def test_untrusted_redirect_is_never_requested(url):
    session = Session([Response(302, location=url)])
    with pytest.raises(AuthenticationError):
        await follow(session, BASE)
    assert session.request.call_count == 1


@pytest.mark.parametrize(
    "page",
    [
        "{}",
        '{"csrf":"ok"}',
        json.dumps({"csrf": "", "transId": "tx"}),
        json.dumps({"csrf": "x" * 16001, "transId": "tx"}),
        json.dumps({"csrf": "x\nsecret", "transId": "tx"}),
    ],
)
def test_reject_changed_or_unsafe_page(page):
    with pytest.raises(ProtocolError):
        login_fields(page)


@pytest.mark.parametrize(
    "status,body,error",
    [
        (400, "secret", AuthenticationError),
        (200, '{"status":400,"message":"secret"}', AuthenticationError),
        (200, "[]", AuthenticationError),
        (200, "not-json-secret", ProtocolError),
        (429, "secret", ConnectionError),
        (500, "secret", ConnectionError),
    ],
)
async def test_submission_errors_never_echo_provider_content(status, body, error):
    session = Session([Response(body=PAGE), Response(status, body)])
    with patch(
        "custom_components.flame_connect.adapters.cloud.credential_login.aiohttp.ClientSession", return_value=session
    ):
        with pytest.raises(error) as caught:
            await CredentialLogin().authorize(create_transaction(), "email", "password")
    assert "secret" not in str(caught.value)
    assert session.closed


@pytest.mark.parametrize("response", [Response(403), Response(302), Response(200, "additional-verification")])
async def test_confirmation_requires_native_callback(response):
    session = Session([Response(body=PAGE), Response(body='{"status":200}'), response])
    with patch(
        "custom_components.flame_connect.adapters.cloud.credential_login.aiohttp.ClientSession", return_value=session
    ):
        with pytest.raises(AuthenticationError):
            await CredentialLogin().authorize(create_transaction(), "email", "password")


async def test_response_and_redirect_bounds():
    session = Session([Response(body="x" * (2 * 1024 * 1024 + 1))])
    with pytest.raises(ProtocolError):
        await request(session, "GET", BASE)
    session = Session([Response(302, location=BASE)] * 20)
    with pytest.raises(AuthenticationError, match="Too many"):
        await follow(session, BASE)
    assert session.request.call_count == 20


@pytest.mark.parametrize("error", [aiohttp.ClientError("secret-password"), TimeoutError("secret-password")])
async def test_network_errors_are_sanitized(error):
    session = Session([error])
    with patch(
        "custom_components.flame_connect.adapters.cloud.credential_login.aiohttp.ClientSession", return_value=session
    ):
        with pytest.raises(ConnectionError) as caught:
            await CredentialLogin().authorize(create_transaction(), "email", "password")
    assert "secret-password" not in str(caught.value)
    assert session.closed


@pytest.mark.parametrize(
    "policy,email,password",
    [
        ("social", "email", "password"),
        ("normal", "", "password"),
        ("normal", "email", ""),
        ("normal", "e" * 513, "password"),
        ("normal", "email", "p" * 4097),
    ],
)
async def test_input_rejected_before_network(policy, email, password):
    with patch("custom_components.flame_connect.adapters.cloud.credential_login.aiohttp.ClientSession") as factory:
        with pytest.raises(AuthenticationError):
            await CredentialLogin().authorize(create_transaction(policy), email, password)
    factory.assert_not_called()
