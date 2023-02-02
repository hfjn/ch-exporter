import asyncio
from asyncio import TaskGroup

import prometheus_client

from ch_exporter.collectors import MetricsGroupCollector
from ch_exporter.config import ExporterConfig
from ch_exporter.healthchecks import health_checks
from ch_exporter.metrics import load_metrics


async def run_loop():
    config = ExporterConfig()
    metrics = load_metrics(config.metric_config_path)
    collectors = [MetricsGroupCollector(config, metric) for metric in metrics.groups]
    prometheus_client.start_http_server(config.prometheus_port)

    async with TaskGroup() as tg:
        for host, url in zip(config.ch_hosts, config.url):
            for collector in collectors:
                tg.create_task(collector.collect(host, url))
            tg.create_task(health_checks(host, url))

asyncio.run(run_loop())
