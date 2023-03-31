import asyncio

import aiohttp
from loguru import logger

from ch_exporter.metrics import CLICKHOUSE_HEALTH, CLICKHOUSE_REPLICATION_HEALTH


async def _check_url(session, url) -> bool:
    try:
        async with session.get(url, timeout=5) as resp:
            await resp.text()
            logger.debug(resp.status)
            return resp.status == 200
    except asyncio.TimeoutError as e:
        logger.error(e)
        return False
    except aiohttp.client.ClientError as e:
        logger.error(e)
        return False


async def health_checks(host, url):
    logger.debug("Starting healthchecks")
    while True:
        async with aiohttp.ClientSession() as session:
            if await _check_url(session, f"{url}/ping"):
                CLICKHOUSE_HEALTH.labels(host).state("healthy")
                logger.debug("Node healthy")
            else:
                CLICKHOUSE_HEALTH.labels(host).state("unhealthy")
                logger.debug("Node unhealthy")

            if await _check_url(
                session,
                f"{url}/replicas_status",
            ):
                CLICKHOUSE_REPLICATION_HEALTH.labels(host).state("healthy")
                logger.debug("Replication Status healthy")
            else:
                CLICKHOUSE_REPLICATION_HEALTH.labels(host).state("unhealthy")
                logger.debug("Replication Status unhealthy")

        await asyncio.sleep(5)
