"""Asynchronous Python client for Poolside pool controllers."""

from .client import (
    ConnectionListener,
    PoolsideAuthError,
    PoolsideClient,
    PoolsideCommandError,
    PoolsideConnectionError,
    StatusListener,
)
from .models import (
    PoolsideControl,
    PoolsideDevice,
    PoolsideGroup,
    PoolsideSite,
    parse_control_layout,
    parse_pool_devices,
)
from .noise_transport import (
    NoiseSession,
    NoiseTransportError,
    fingerprint,
    generate_keypair,
    public_key_from_private,
)
from .pairing import (
    PairingApproved,
    PairingBusy,
    PairingError,
    PairingInvalid,
    PairingPending,
    PairingRejected,
    PairingTimedOut,
    async_await_pairing_result,
    async_request_pairing,
)

__version__ = "0.1.0"

__all__ = [
    "ConnectionListener",
    "NoiseSession",
    "NoiseTransportError",
    "PairingApproved",
    "PairingBusy",
    "PairingError",
    "PairingInvalid",
    "PairingPending",
    "PairingRejected",
    "PairingTimedOut",
    "PoolsideAuthError",
    "PoolsideClient",
    "PoolsideCommandError",
    "PoolsideConnectionError",
    "PoolsideControl",
    "PoolsideDevice",
    "PoolsideGroup",
    "PoolsideSite",
    "StatusListener",
    "async_await_pairing_result",
    "async_request_pairing",
    "fingerprint",
    "generate_keypair",
    "parse_control_layout",
    "parse_pool_devices",
    "public_key_from_private",
]
