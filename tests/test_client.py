"""Tests for PoolsideClient's optimistic desired-state tracking."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from aiopoolside.client import (
    PoolsideClient,
    PoolsideCommandError,
    PoolsideConnectionError,
)


@pytest.fixture
def send_request() -> AsyncMock:
    """A stub for PoolsideClient.async_send_request (no real connection)."""
    return AsyncMock(return_value=True)


@pytest.fixture
def client(send_request: AsyncMock) -> PoolsideClient:
    """A PoolsideClient with async_send_request stubbed out (no real connection)."""
    instance = PoolsideClient(
        session=MagicMock(spec=aiohttp.ClientSession),
        host="192.168.1.50",
        port=8126,
        client_private_key=b"\x01" * 32,
        controller_public_key=b"\x02" * 32,
        controller_uuid="controller-1",
    )
    instance.async_send_request = send_request  # type: ignore[method-assign]
    return instance


async def test_set_desired_state_records_optimistic_status(
    client: PoolsideClient,
) -> None:
    """A successful write is recorded under the control's own UUID."""
    await client.async_set_desired_state("control-1", Status="ON", PowerLevel="75")

    assert client.get_status("control-1", "Status") == "ON"
    assert client.get_status("control-1", "PowerLevel") == "75"


async def test_set_desired_state_notifies_subscribers(client: PoolsideClient) -> None:
    """Subscribers for the control's UUID are notified after a successful write."""
    calls = []
    client.subscribe_status("control-1", lambda: calls.append(True))

    await client.async_set_desired_state("control-1", Status="ON")

    assert calls == [True]


async def test_set_desired_state_sends_batch_and_control_uuid(
    client: PoolsideClient, send_request: AsyncMock
) -> None:
    """The JSON-RPC call carries a fresh BatchUUID and the target ControlUUID."""
    await client.async_set_desired_state("control-1", Status="ON")

    method, params = send_request.call_args.args
    assert method == "Device.setDesiredState2"
    assert params["DesiredStates"] == [{"ControlUUID": "control-1", "Status": "ON"}]
    assert "BatchUUID" in params


async def test_refresh_status_calls_get_status(
    client: PoolsideClient, send_request: AsyncMock
) -> None:
    """async_refresh_status calls the bare Device.getStatus (no Items filter)."""
    send_request.return_value = []

    await client.async_refresh_status()

    send_request.assert_awaited_with("Device.getStatus", {})


async def test_refresh_status_applies_every_returned_item(
    client: PoolsideClient, send_request: AsyncMock
) -> None:
    """Every item in the getStatus response is applied, as if it were a push."""
    send_request.return_value = [
        {"UUID": "control-1", "name": "ActualPowerState", "value": "ON"},
        {"UUID": "control-2", "name": "Temperature", "value": 79},
    ]

    await client.async_refresh_status()

    assert client.get_status("control-1", "ActualPowerState") == "ON"
    assert client.get_status("control-2", "Temperature") == 79


@pytest.mark.parametrize(
    "error", [PoolsideConnectionError("offline"), PoolsideCommandError("rejected")]
)
async def test_refresh_status_swallows_errors(
    client: PoolsideClient, send_request: AsyncMock, error: Exception
) -> None:
    """A failed getStatus call is logged, not raised - it shouldn't break connect()."""
    send_request.side_effect = error

    await client.async_refresh_status()


async def test_refresh_status_times_out(
    client: PoolsideClient, send_request: AsyncMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unanswered getStatus gives up instead of stalling connect() forever."""
    monkeypatch.setattr("aiopoolside.client.PING_TIMEOUT", 0.01)

    async def never_answers(*_args: object) -> None:
        await asyncio.Event().wait()

    send_request.side_effect = never_answers

    await asyncio.wait_for(client.async_refresh_status(), 1)


async def test_reconnect_loop_survives_unexpected_error(
    client: PoolsideClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An unexpected error from a reconnect attempt is logged and retried."""
    monkeypatch.setattr("aiopoolside.client.RECONNECT_INITIAL_DELAY", 0)
    calls = 0

    async def connect_once() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("boom")
        client._closing = True
        client._receive_task = _finished_task()

    client._async_connect_once = connect_once  # type: ignore[method-assign]
    client._receive_task = _finished_task()

    await asyncio.wait_for(client._async_reconnect_loop(), 1)

    assert calls == 2
    assert "Unexpected error while reconnecting" in caplog.text


async def test_reconnect_loop_survives_failed_receive_loop(
    client: PoolsideClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A receive loop that dies with an error still leads to a reconnect."""
    monkeypatch.setattr("aiopoolside.client.RECONNECT_INITIAL_DELAY", 0)
    calls = 0

    async def failing_receive_loop() -> None:
        raise RuntimeError("bad message")

    async def connect_once() -> None:
        nonlocal calls
        calls += 1
        client._closing = True
        client._receive_task = _finished_task()

    client._async_connect_once = connect_once  # type: ignore[method-assign]
    client._receive_task = asyncio.ensure_future(failing_receive_loop())

    await asyncio.wait_for(client._async_reconnect_loop(), 1)

    assert calls == 1
    assert "Receive loop failed" in caplog.text


def _finished_task() -> asyncio.Future[None]:
    """Return an already-completed future standing in for a receive task."""
    future: asyncio.Future[None] = asyncio.get_running_loop().create_future()
    future.set_result(None)
    return future
