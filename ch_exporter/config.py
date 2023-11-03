from pathlib import Path
from typing import List, Union

import yaml
from aiochclient import ChClient
from aiohttp import ClientSession
from pydantic import BaseSettings, validator

from ch_exporter.hosts import Host
from ch_exporter.metrics import ClickhouseMetricGroup


class ExporterConfig(BaseSettings):
    ch_hosts: Union[str, List[str]]
    ch_http_port: int
    ch_user: str
    ch_password: str
    ch_macros: Union[str, List[str]]
    metrics_path: Path = "metrics.yaml"
    prefix: str = "clickhouse_exporter"
    prometheus_port: int = 8080
    metrics: List[ClickhouseMetricGroup] = None

    def __init__(self, **data):
        super().__init__(**data)
        config = yaml.safe_load(self.metrics_path.read_text())
        self.metrics = [ClickhouseMetricGroup(**group) for group in config.get("groups")]

    @validator("ch_hosts", pre=True)
    def _split_hosts(cls, ch_hosts):
        return [host for host in ch_hosts.split(",")]

    @validator("ch_macros", pre=True)
    def _split_macros(cls, ch_macros):
        return [macro for macro in ch_macros.split(",")]

    class Config:
        env_prefix = "ch_exporter_"


async def load_hosts(config: ExporterConfig) -> List[Host]:
    hosts = []
    async with ClientSession() as session:
        for host in config.ch_hosts:
            h = Host(name=host, port=config.ch_http_port)
            client = ChClient(
                session=session,
                url=h.url,
                user=config.ch_user,
                password=config.ch_password,
            )
            if config.ch_macros:
                macros = [f"'{macro}'" for macro in config.ch_macros]
                result = await client.fetch(f"SELECT * FROM system.macros WHERE macro in ({','. join(macros)})")
                h.labels = {macro["macro"]: macro["substitution"] for macro in result}
                hosts.append(h)

    return hosts
