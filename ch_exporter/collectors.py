import asyncio

from aiochclient import ChClient, ChClientError
from aiohttp import ClientConnectorError, ClientSession
from loguru import logger
from pendulum import now

from ch_exporter.config import ExporterConfig
from ch_exporter.metrics import ClickhouseMetricGroup, generate_prometheus_metric


class MetricsGroupCollector:
    def __init__(self, config: ExporterConfig, group: ClickhouseMetricGroup):
        self._config = config
        self.query = group.query
        self.labels = group.labels
        self.metrics = group.metrics
        self.period = group.period_s
        self.specific_host = group.specific_host
        for metric in self.metrics:
            # Need to generate with all labels here to have
            # spot for automatically filled in labels (e.g. node)
            metric.prometheus_metric = generate_prometheus_metric(metric, group.all_labels)

    @property
    def metric_names(self) -> str:
        return ", ".join([m.name for m in self.metrics])

    async def collect(self, node, url):
        logger.debug(f"Starting collection of {', '.join([metric.name for metric in self.metrics])}")
        async with ClientSession():
            client = ChClient(
                url=url,
                user=self._config.ch_user,
                password=self._config.ch_password,
            )
            while True:
                start_time = now()
                try:
                    result = await client.fetch(self.query)
                    for line in result:
                        labels = [line[label] for label in self.labels] + [node]
                        for metric in self.metrics:
                            metric.prometheus_metric.labels(*labels).__getattribute__(metric.observe_function)(line[metric.observation])
                except ChClientError as e:
                    logger.error("Error while collecting metric: ", e)
                except ClientConnectorError as e:
                    logger.error(f"HTTP Error reaching clickhouse {url}: ", e)
                time_taken = (now() - start_time).seconds
                await asyncio.sleep(self.period - time_taken)
