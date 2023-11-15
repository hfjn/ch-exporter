import asyncio
import datetime
from typing import List

import aiohttp
from loguru import logger
from prometheus_client import Enum, CollectorRegistry

from ch_exporter.hosts import Host


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


async def healthcheck(host: Host, clickhouse_health: Enum, clickhouse_replication_health: Enum):
    labels = [host.name] + host.macro_values
    logger.info(f"Starting healthcheck with {labels}")
    while True:
        async with aiohttp.ClientSession() as session:
            if await _check_url(session, f"{host.url}/ping"):
                clickhouse_health.labels(*labels).state("healthy")
                host.node_healthy = True
                logger.debug("Node healthy")
            else:
                clickhouse_health.labels(*labels).state("unhealthy")
                host.node_healthy = False
                logger.debug("Node unhealthy")

            if await _check_url(
                    session,
                    f"{host.url}/replicas_status",
            ):
                clickhouse_replication_health.labels(labels).state("healthy")
                host.replication_healthy = True
                logger.debug("Replication Status healthy")
            else:
                clickhouse_replication_health.labels(labels).state("unhealthy")
                host.replication_healthy = False
                logger.debug("Replication Status unhealthy")
            host.last_check = datetime.datetime.now()

        await asyncio.sleep(30)
