# aiopoolside

Asynchronous Python client for Poolside pool controllers.

Speaks the controller's local protocol: an encrypted JSON-RPC transport over
websockets using the Noise Protocol Framework
(`Noise_XX_25519_ChaChaPoly_SHA256`), plus the plaintext pre-auth pairing
handshake used to enroll a new client.

## Installation

```bash
pip install aiopoolside
```

## Usage

```python
import aiohttp

from aiopoolside import (
    PoolsideClient,
    async_await_pairing_result,
    async_request_pairing,
    generate_keypair,
)


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        # One-time pairing: the user approves the request on the controller.
        private_key, public_key = generate_keypair()
        ws, result = await async_request_pairing(
            session, "192.168.1.50", 8126, "My Client", public_key
        )
        approved = await async_await_pairing_result(ws)

        client = PoolsideClient(
            session=session,
            host="192.168.1.50",
            port=8126,
            client_private_key=private_key,
            controller_public_key=approved.controller_public_key,
            controller_uuid=approved.controller_uuid,
        )
        await client.async_connect()
        site, controls = await client.async_get_control_layout()
        try:
            for control in controls:
                print(control.name, control.control_type)
        finally:
            await client.async_disconnect()
```

## Development

```bash
uv sync
uv run pytest
```

## License

MIT
