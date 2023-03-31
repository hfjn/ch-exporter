from pathlib import Path
from typing import List, Optional

import prometheus_client
import yaml
from loguru import logger
from prometheus_client import Enum
from prometheus_client.metrics_core import METRIC_TYPES, Metric
from pydantic import BaseModel, root_validator, validator

METRIC_FUNCTIONS = {
    "Summary": "observe",
    "Histogram": "observe",
    "Counter": "inc",
    "Enum": "state",
    "Gauge": "set",
}

DEFAULT_LABELS = ["clickhouse_node"]
PREFIX = "ch_exporter"

CLICKHOUSE_HEALTH = Enum(
    PREFIX + "_node_health",
    "Clickhouse Nodes Health Status",
    states=["healthy", "unhealthy"],
    labelnames=DEFAULT_LABELS,
)
CLICKHOUSE_REPLICATION_HEALTH = Enum(
    PREFIX + "_replication_status",
    "Clickhouse Nodes Replication Status",
    states=["healthy", "unhealthy"],
    labelnames=DEFAULT_LABELS,
)


class CHMetric(BaseModel):
    name: str
    description: str
    observation: str
    metric: str
    buckets: Optional[str] = None
    start: Optional[float] = None
    factor: Optional[float] = None
    size: Optional[float] = None
    count: Optional[int] = None
    prometheus_metric: None = None


    @property
    def prefixed_name(self) -> str:
        return f"{PREFIX}_{self.name}"

    @property
    def observe_function(self) -> str:
        return METRIC_FUNCTIONS[self.metric]

    @validator("prometheus_metric", always=True)
    def validate_prometheus_metric(cls, v) -> None:
        if v:
            raise ValueError("This value must be kept empty. It's a placeholder and set during runtime")
        return v

    @validator("metric")
    def validate_metric(cls, v):
        if v not in list(METRIC_FUNCTIONS.keys()):
            raise ValueError(f"Metric Type {v} invalid. Must be one of {METRIC_TYPES}")
        return v

    @validator("start")
    def validate_start(cls, v):
        if v < 0:
            raise ValueError("Start needs to be positive")
        return v

    @validator("factor")
    def validate_factor(cls, v):
        if v < 2:
            raise ValueError("Factor needs to be a float of at least 2")
        return v

    @validator("count")
    def validate_count(cls, v):
        if v < 2:
            raise ValueError("Count needs to be at least 2")
        return v

    @root_validator()
    def validate_buckets(cls, values):
        if values.get("metric") != "Histogram":
            return values
        if values.get("buckets") not in ["Exponential", "Linear"]:
            raise ValueError("Bucket can only be of Exponential or Linear Type")
        if values.get("buckets") == "Exponential" and values.get("start") and values.get("factor") and values.get("count"):
            return values
        if values.get("buckets") == "Linear" and values.get("start") and values.get("size") and values.get("count"):
            return values
        raise ValueError("Exponential Buckets needs start, factor and count params, Linear needs start, size and count")


class ClickhouseMetricGroup(BaseModel):
    labels: List[str]
    query: str
    specific_host: Optional[str] = None
    metrics: List[CHMetric]
    timeout_s: int = 5
    period_s: int = 10

    @property
    def all_labels(self):
        return self.labels + DEFAULT_LABELS


class Metrics(BaseModel):
    groups: List[ClickhouseMetricGroup]


def load_metrics(path: Path) -> Metrics:
    return Metrics(**yaml.safe_load(path.read_text()))


def _exponential_buckets(start: float, factor: float, count: int) -> List[float]:
    buckets = []
    for bucket in range(count):
        buckets.append(start)
        start *= factor
    return buckets


def _linear_buckets(start: float, size: float, count: int) -> List[float]:
    buckets = []
    for bucket in range(count):
        buckets.append(start)
        start += size
    return buckets


def generate_prometheus_metric(metric: CHMetric, labels: List[str]):
    class_ = getattr(prometheus_client, metric.metric)
    logger.debug(f"Creating Metric {metric.prefixed_name} of type {metric.metric} with labels {labels}")
    return class_(metric.prefixed_name, metric.description, labels)
