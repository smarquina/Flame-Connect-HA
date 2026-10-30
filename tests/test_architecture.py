"""Prevent framework and infrastructure imports from crossing inward boundaries."""

import ast
from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components/flame_connect"


def test_hexagonal_dependency_direction():
    for layer in ["domain", "application"]:
        for path in (ROOT / layer).rglob("*.py"):
            tree = ast.parse(path.read_text())
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            for module in imports:
                assert not any(
                    part in module.split(".") for part in ["homeassistant", "aiohttp", "jwt", "adapters", "client"]
                ), f"{path}: dependency points outward to {module}"
                if layer == "domain":
                    assert "application" not in module.split(".")


async def test_use_case_never_replays_unknown_outcome(overview):
    from unittest.mock import AsyncMock

    import pytest

    from custom_components.flame_connect.adapters.cloud.codec import decode_state
    from custom_components.flame_connect.application.fireplaces import FireplaceService
    from custom_components.flame_connect.domain.errors import CommandError

    gateway = AsyncMock()
    gateway.overview.return_value = decode_state("fixture-fire", overview)
    gateway.write.side_effect = CommandError("outcome unknown")
    service = FireplaceService(gateway, "fixture-fire")
    with pytest.raises(CommandError):
        await service.execute(lambda state: state.power(True))
    gateway.write.assert_awaited_once()
    gateway.overview.assert_awaited_once()
