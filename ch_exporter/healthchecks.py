import asyncio
import datetime

import aiohttp
from loguru import logger

from ch_exporter.hosts import Host
from ch_exporter.metrics import CLICKHOUSE_HEALTH, CLICKHOUSE_REPLICATION_HEALTH


async def _check_url(session, url) -> bool:
    try:
        async with session.get(url, timeout=15) as resp:
            await resp.text()
            logger.debug(resp.status)
            return resp.status == 200
    except asyncio.TimeoutError as e:
        logger.error(e)
        return False
    except aiohttp.client.ClientError as e:
        logger.error(e)
        return False


async def healthchecks(host: Host):
    logger.debug("Starting healthchecks")
    while True:
        async with aiohttp.ClientSession() as session:
            if await _check_url(session, f"{host.url}/ping"):
                CLICKHOUSE_HEALTH.labels(host).state("healthy")
                host.node_healthy = True
                logger.debug("Node healthy")
            else:
                CLICKHOUSE_HEALTH.labels(host).state("unhealthy")
                host.node_healthy = False
                logger.debug("Node unhealthy")

            if await _check_url(
                    session,
                    f"{host.url}/replicas_status",
            ):
                CLICKHOUSE_REPLICATION_HEALTH.labels(host).state("healthy")
                host.replication_healthy = True
                logger.debug("Replication Status healthy")
            else:
                CLICKHOUSE_REPLICATION_HEALTH.labels(host).state("unhealthy")
                host.replication_healthy = False
                logger.debug("Replication Status unhealthy")
            host.last_check = datetime.datetime.now()

        await asyncio.sleep(30)
