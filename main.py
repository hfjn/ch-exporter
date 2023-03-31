import asyncio
from asyncio import TaskGroup

import prometheus_client
from loguru import logger

from ch_exporter.collectors import MetricsGroupCollector
from ch_exporter.config import ExporterConfig
from ch_exporter.healthchecks import health_checks
from ch_exporter.metrics import load_metrics


async def run_loop():
    config = ExporterConfig()
    metrics = load_metrics(config.metric_config_path)
    collectors = [MetricsGroupCollector(config, metric) for metric in metrics.groups]

    logger.info("Starting http endpoint")
    prometheus_client.start_http_server(config.prometheus_port)
    logger.info("Starting collection loop...")
    async with TaskGroup() as tg:
        for host, url in zip(config.ch_hosts, config.url):
            for collector in collectors:
                if collector.specific_host and collector.specific_host != host:
                    continue
                logger.info(f"Adding collectors for {collector.metric_names} on host {host}")
                tg.create_task(collector.collect(host, url))

            tg.create_task(health_checks(host, url))


asyncio.run(run_loop())
