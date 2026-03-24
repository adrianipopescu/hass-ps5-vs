import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

_DDP_PORT = 9302
_DDP_MSG = b"SRCH * HTTP/1.1\ndevice-discovery-protocol-version:00030010\n"


async def discover_ps5(host: str | None = None) -> dict | None:
    """DDP search — unicast to host if given, otherwise broadcast."""
    loop = asyncio.get_running_loop()
    target = (host, _DDP_PORT) if host else ("255.255.255.255", _DDP_PORT)
    found: asyncio.Future = loop.create_future()
    transport = None

    class _Proto(asyncio.DatagramProtocol):
        def datagram_received(self, data, addr):
            if found.done():
                return
            text = data.decode("utf-8", errors="ignore")
            if "host-type:PS5" not in text:
                return
            info = {}
            for line in text.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    info[k.strip().lower()] = v.strip()
            found.set_result({
                "host": addr[0],
                "mac": info.get("host-id", ""),
                "name": info.get("host-name", "PS5"),
            })

        def error_received(self, exc):
            if not found.done():
                found.cancel()

    try:
        transport, _ = await loop.create_datagram_endpoint(
            _Proto,
            local_addr=("0.0.0.0", 0),
            allow_broadcast=True,
        )
        transport.sendto(_DDP_MSG, target)
        return await asyncio.wait_for(asyncio.shield(found), timeout=3.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        return None
    except Exception as err:
        _LOGGER.debug("PS5 DDP discovery error: %s", err)
        return None
    finally:
        if transport:
            transport.close()
