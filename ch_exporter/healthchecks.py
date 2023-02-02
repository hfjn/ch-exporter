import asyncio

import aiohttp
from loguru import logger

from ch_exporter.metrics import CLICKHOUSE_HEALTH, CLICKHOUSE_REPLICATION_HEALTH


async def _check_url(session, url) -> bool:
    async with session.get(url, timeout=1) as resp:
        await resp.text()
        return resp.status == 200


async def health_checks(host, url):
    logger.debug("Starting healthchecks")
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                if await _check_url(session, f"{url}/ping"):
                    CLICKHOUSE_HEALTH.labels(host).state("healthy")
                    logger.debug("Node healthy")
                else:
                    CLICKHOUSE_HEALTH.labels(host).state("unhealthy")
                    logger.debug("Node unhealthy")

                if await _check_url(
                    session,
                    f"{url}/replica_status",
                ):
                    CLICKHOUSE_REPLICATION_HEALTH.labels(host).state("healthy")
                else:
                    CLICKHOUSE_REPLICATION_HEALTH.labels(host).state("unhealthy")
        except aiohttp.client.ClientError as e:
            logger.error(e)
            CLICKHOUSE_HEALTH.labels(host).state("unhealthy")
            CLICKHOUSE_REPLICATION_HEALTH.labels(host).state("unhealthy")
        await asyncio.sleep(5)
