import asyncio

from aiochclient import ChClient, ChClientError
from aiohttp import ClientError, ClientSession
from loguru import logger
from pendulum import now
from prometheus_client import CollectorRegistry

from ch_exporter.config import ExporterConfig
from ch_exporter.hosts import Host
from ch_exporter.metrics import ClickhouseMetricGroup


class MetricsGroupCollector:
    def __init__(self, registry: CollectorRegistry, config: ExporterConfig, group: ClickhouseMetricGroup):
        self._config = config
        self.query = group.query
        self.labels = group.labels
        self.metrics = group.metrics
        self.period = group.period_s
        self.specific_host = group.specific_host

        group.init_for_collector(registry, [k for k in sorted(config.ch_macros)])

    @property
    def metric_names(self) -> str:
        return ", ".join([m.name for m in self.metrics])

    async def collect(self, host: Host):
        hostname = host
        logger.debug(f"Starting collection of {', '.join([metric.name for metric in self.metrics])}")
        async with ClientSession() as session:
            client = ChClient(
                session=session,
                url=host.url,
                user=self._config.ch_user,
                password=self._config.ch_password,
            )
            while True:
                start_time = now()
                try:
                    result = await client.fetch(self.query)
                    for metric in self.metrics:
                        metric.clear(host.name)
                        for line in result:
                            label_values = [line[label] for label in self.labels]
                            metric.observe(hostname, label_values, line[metric.observation])
                except ChClientError as e:
                    logger.exception(f"{self.metric_names}: Error while collecting metric: ", e)
                except ClientError as e:
                    logger.exception(f"{self.metric_names}: HTTP Error reaching clickhouse {host.url}: ", e)
                except asyncio.TimeoutError as e:
                    logger.exception(f"{self.metric_names}: HTTP Timeout reaching clickhouse {host.url}: ", e)

                time_taken = (now() - start_time).seconds
                await asyncio.sleep(self.period - time_taken)
