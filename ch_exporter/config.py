from pathlib import Path
from typing import List, Union

from pydantic import BaseSettings, validator


class ExporterConfig(BaseSettings):
    ch_hosts: Union[str, List[str]]
    ch_http_port: int
    ch_user: str
    ch_password: str
    metric_config_path: Path = "metrics.yaml"
    prefix: str = "clickhouse_exporter"
    prometheus_port: int = 8080

    @validator("ch_hosts", pre=True)
    def _split_hosts(cls, ch_hosts):
        if isinstance(ch_hosts, str):
            return [item.strip() for item in ch_hosts.split(",")]
        return ch_hosts

    @property
    def url(self) -> List[str]:
        return [f"http://{host}:{self.ch_http_port}" for host in self.ch_hosts]

    class Config:
        env_prefix = "ch_exporter_"
