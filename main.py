import asyncio
import sys
from asyncio import TaskGroup

import prometheus_client
from loguru import logger

from ch_exporter.collectors import MetricsGroupCollector
from ch_exporter.config import ExporterConfig, load_hosts
from ch_exporter.healthchecks import healthchecks


async def run_loop():
    config = ExporterConfig()
    hosts = await load_hosts(config)  # Needs to be called from main event loop since pydantic is sync
    collectors = [MetricsGroupCollector(config, metric) for metric in config.metrics]

    logger.info("Starting http endpoint")
    prometheus_client.start_http_server(config.prometheus_port)
    logger.info("Starting collection loop...")
    async with TaskGroup() as tg:
        for host in hosts:
            hostname = host.name
            for collector in collectors:
                if collector.specific_host and collector.specific_host != hostname:
                    continue
                logger.info(f"Adding collectors for {collector.metric_names} on host {hostname}")
                tg.create_task(collector.collect(host))

            tg.create_task(healthchecks(host))


asyncio.run(run_loop())
