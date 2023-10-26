from collections import defaultdict
from typing import Any, List, Optional, Sequence, Tuple

import prometheus_client
from loguru import logger
from prometheus_client import Enum
from prometheus_client.metrics_core import METRIC_TYPES
from pydantic import BaseModel, PrivateAttr, root_validator, validator

from ch_exporter.hosts import Host

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

    _prometheus_metric: Any = PrivateAttr()
    _active_label_values_by_node: dict[str, set[tuple[str]]] = PrivateAttr(default_factory=lambda: defaultdict(set))

    @property
    def prefixed_name(self) -> str:
        return f"{PREFIX}_{self.name}"

    @property
    def observe_function(self) -> str:
        return METRIC_FUNCTIONS[self.metric]

    def init_for_collector(self, all_labels: Sequence[str]):
        class_ = getattr(prometheus_client, self.metric)
        logger.debug(f"Creating Metric {self.prefixed_name} of type {self.metric} with labels {all_labels}")
        self._prometheus_metric = class_(self.prefixed_name, self.description, all_labels)

    def observe(self, host: Host, label_values: Sequence[str], value: Any):
        all_label_values = tuple(str(v) for v in label_values) + tuple(host.labels.values()) + (host.name,)g
        self._prometheus_metric.labels(*all_label_values).__getattribute__(self.observe_function)(value)
        self._active_label_values_by_node[host.name].add(all_label_values)

    def clear(self, node: str):
        for label_values in self._active_label_values_by_node[node]:
            self._prometheus_metric.remove(*label_values)
        self._active_label_values_by_node[node].clear()

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
        if values.get("buckets") == "Exponential" and values.get("start") and values.get("factor") and values.get(
                "count"):
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
    def all_labels(self) -> List[str]:
        return self.labels + DEFAULT_LABELS

    def init_for_collector(self, macros: Optional[List[str]] = None):
        for metric in self.metrics:
            metric.init_for_collector(self.all_labels + macros)


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
