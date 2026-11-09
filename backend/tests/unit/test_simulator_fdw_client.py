"""Per-loop httpx client for journey stages that spin temporary event loops."""

import asyncio

from src.services import simulator_fdw_client as sfc


def test_get_simulator_http_client_per_loop():
    sfc._clients_by_loop.clear()
    sfc._SHARED_CLIENT = None

    loop_a = asyncio.new_event_loop()
    try:
        loop_a.run_until_complete(_client_id())
        id_a = loop_a.run_until_complete(_client_id())
    finally:
        loop_a.close()

    loop_b = asyncio.new_event_loop()
    try:
        id_b = loop_b.run_until_complete(_client_id())
    finally:
        loop_b.close()

    assert id_a != id_b


async def _client_id() -> int:
    return id(sfc.get_simulator_http_client())
