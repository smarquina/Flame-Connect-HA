from dataclasses import replace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.flame_connect.adapters.cloud.codec import decode_fireplace
from custom_components.flame_connect.adapters.cloud.tokens import decode_tokens
from custom_components.flame_connect.const import DOMAIN
from custom_components.flame_connect.domain.errors import AuthenticationError, ConnectionError, ProtocolError


@pytest.fixture
def link_api(tokens, fire):
    with (
        patch("custom_components.flame_connect.composition.B2C") as provider,
        patch("custom_components.flame_connect.composition.FlameClient") as api,
        patch("custom_components.flame_connect.async_setup_entry", AsyncMock(return_value=True)),
    ):
        provider.return_value.exchange = AsyncMock(return_value=decode_tokens(tokens))
        api.return_value.fires = AsyncMock(return_value=[decode_fireplace(fire)])
        yield provider.return_value, api.return_value


async def start(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"policy": "normal", "login_method": "browser"}
    )


async def test_full_flow(hass, link_api):
    result = await start(hass)
    assert result["step_id"] == "link"
    assert "code_challenge_method=S256" in result["description_placeholders"]["authorize_url"]
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"callback_url": "msal-return"})
    assert result["step_id"] == "devices"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"fires": ["fixture-fire"], "temperature_unit": "C"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "fixture-account"
    assert result["data"]["fires"] == ["fixture-fire"]
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    "error,expected",
    [
        (AuthenticationError(), "invalid_auth"),
        (ConnectionError(), "cannot_connect"),
        (ProtocolError(), "invalid_response"),
    ],
)
async def test_error_recovery(hass, link_api, error, expected):
    provider, _ = link_api
    tokens = provider.exchange.return_value
    provider.exchange.side_effect = error
    result = await start(hass)
    url = result["description_placeholders"]["authorize_url"]
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"callback_url": "bad"})
    assert result["errors"] == {"base": expected}
    assert result["description_placeholders"]["authorize_url"] != url
    provider.exchange.side_effect = None
    provider.exchange.return_value = tokens
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"callback_url": "new"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"fires": ["fixture-fire"], "temperature_unit": "auto"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "fixture-account"
    await hass.async_block_till_done()


async def test_duplicate(hass, entry, link_api):
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"callback_url": "return"})
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "fires,reason", [([], "no_devices"), ([{"FireId": "ble", "IsIotFire": False}], "no_wifi_devices")]
)
async def test_no_compatible_devices(hass, link_api, fires, reason):
    link_api[1].fires.return_value = [decode_fireplace(fire) for fire in fires]
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"callback_url": "return"})
    assert result["reason"] == reason


async def test_empty_selection(hass, link_api):
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"callback_url": "return"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"fires": [], "temperature_unit": "auto"}
    )
    assert result["errors"] == {"base": "select_device"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"fires": ["fixture-fire"], "temperature_unit": "F"}
    )
    assert result["result"].unique_id == "fixture-account"
    await hass.async_block_till_done()


async def test_refresh_required(hass, link_api):
    provider, _ = link_api
    provider.exchange.return_value = replace(provider.exchange.return_value, refresh_token=None)
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"callback_url": "return"})
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth(hass, entry, link_api):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reauth", "entry_id": entry.entry_id}, data=entry.data
    )
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"policy": "normal", "login_method": "browser"}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"callback_url": "return"})
    assert result["reason"] == "reauth_successful"
    await hass.async_block_till_done()


async def test_reauth_wrong_account(hass, entry, link_api):
    provider, _ = link_api
    provider.exchange.return_value = replace(provider.exchange.return_value, account_id="other")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reauth", "entry_id": entry.entry_id}, data=entry.data
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"policy": "normal", "login_method": "browser"}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"callback_url": "return"})
    assert result["reason"] == "unique_id_mismatch"


async def test_options(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"temperature_unit": "F", "experimental_controls": True}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["temperature_unit"] == "F"


async def test_direct_link_entrypoint(hass, link_api):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "link"})
    assert result["step_id"] == "link"
    hass.config_entries.flow.async_abort(result["flow_id"])


async def test_configure_preserves_rotated_token(hass, link_api, tokens):
    provider, client = link_api
    original = tokens
    from custom_components.flame_connect.application.tokens import TokenManager

    managers = []

    def factory(provider, tokens, save):
        manager = TokenManager(provider, tokens, save)
        managers.append(manager)
        return manager

    async def fires():
        await managers[0].save(decode_tokens({**original, "refresh_token": "rotated"}))
        return [decode_fireplace({"FireId": "fixture-fire", "IsIotFire": True})]

    client.fires.side_effect = fires
    with patch("custom_components.flame_connect.composition.TokenManager", side_effect=factory):
        result = await start(hass)
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"callback_url": "return"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"fires": ["fixture-fire"], "temperature_unit": "auto"}
        )
    assert result["data"]["tokens"]["refresh_token"] == "rotated"
    await hass.async_block_till_done()


async def test_reconfigure(hass, entry, link_api):
    with patch.object(hass.config_entries, "async_reload", AsyncMock(return_value=True)):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
        )
        assert result["step_id"] == "devices"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"fires": ["fixture-fire"], "temperature_unit": "F"}
        )
        assert result["reason"] == "reconfigure_successful"
        assert entry.options["temperature_unit"] == "F"
        await hass.async_block_till_done()


async def test_reconfigure_connection_recovery(hass, entry, link_api):
    client = link_api[1]
    fires = client.fires.return_value
    client.fires.side_effect = ConnectionError()
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
    )
    assert result["errors"] == {"base": "cannot_connect"}
    client.fires.side_effect = None
    client.fires.return_value = fires
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"fires": ["fixture-fire"], "temperature_unit": "auto"}
    )
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()


async def test_reconfigure_auth_error(hass, entry, link_api):
    link_api[1].fires.side_effect = AuthenticationError()
    with patch.object(entry, "async_start_reauth") as reauth:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
        )
        assert result["reason"] == "reauthentication_required"
        reauth.assert_called_once()


async def test_reconfigure_persists_rotation(hass, entry, link_api):
    from custom_components.flame_connect.application.tokens import TokenManager

    managers = []

    def factory(provider, tokens, save):
        manager = TokenManager(provider, tokens, save)
        managers.append(manager)
        return manager

    async def fires():
        await managers[0].save(decode_tokens({**entry.data["tokens"], "refresh_token": "rotated"}))
        return [decode_fireplace({"FireId": "fixture-fire", "IsIotFire": True})]

    link_api[1].fires.side_effect = fires
    with patch("custom_components.flame_connect.composition.TokenManager", side_effect=factory):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
        )
    assert entry.data["tokens"]["refresh_token"] == "rotated"
    hass.config_entries.flow.async_abort(result["flow_id"])


async def credentials_start(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"policy": "normal"})
    assert result["step_id"] == "credentials"
    return result


async def test_credentials_flow_persists_only_tokens(hass, link_api):
    result = await credentials_start(hass)
    with patch("custom_components.flame_connect.config_flow.CredentialLogin") as login:
        login.return_value.authorize = AsyncMock(return_value="native-return")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": " test@example.invalid ", "password": "fake-password"}
        )
        assert result["step_id"] == "devices"
        assert login.return_value.authorize.call_args.args[1:] == ("test@example.invalid", "fake-password")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"fires": ["fixture-fire"], "temperature_unit": "auto"}
    )
    assert set(result["data"]) == {"tokens", "fires"}
    assert "fake-password" not in str(result)
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    "error,expected",
    [
        (AuthenticationError(), "credentials_rejected"),
        (ConnectionError(), "cannot_connect"),
        (ProtocolError(), "invalid_response"),
    ],
)
async def test_credentials_errors_allow_browser_fallback(hass, link_api, error, expected):
    result = await credentials_start(hass)
    with patch("custom_components.flame_connect.config_flow.CredentialLogin") as login:
        login.return_value.authorize = AsyncMock(side_effect=error)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "test@example.invalid", "password": "fake-password"}
        )
    assert result["errors"] == {"base": expected}
    assert "fake-password" not in str(result)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"use_browser": True})
    assert result["step_id"] == "link"
    hass.config_entries.flow.async_abort(result["flow_id"])


async def test_social_account_uses_hosted_login(hass, link_api):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"policy": "social"})
    assert result["step_id"] == "link"
    hass.config_entries.flow.async_abort(result["flow_id"])


async def test_credentials_reauth_reuses_account_identity(hass, entry, link_api):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reauth", "entry_id": entry.entry_id}, data=entry.data
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"policy": "normal"})
    with patch("custom_components.flame_connect.config_flow.CredentialLogin") as login:
        login.return_value.authorize = AsyncMock(return_value="native-return")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"email": "test@example.invalid", "password": "fake-password"}
        )
    assert result["reason"] == "reauth_successful"
    assert entry.unique_id == "fixture-account"
    assert "fake-password" not in str(entry.data)
    await hass.async_block_till_done()
