import asyncio
from asyncio import TaskGroup
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException
from loguru import logger
from prometheus_client import CollectorRegistry, Enum
from prometheus_client.registry import CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator

from ch_exporter.collectors import MetricsGroupCollector
from ch_exporter.config import ExporterConfig, load_hosts
from ch_exporter.healthchecks import healthcheck
from ch_exporter.hosts import Host
from ch_exporter.metrics import PREFIX, DEFAULT_LABELS

# Create app
app = FastAPI(debug=True)
REGISTRY = CollectorRegistry(auto_describe=True)

instrumentator = Instrumentator(registry=REGISTRY).instrument(app)


@app.get("/health/{macro}/{macro_id}")
async def get_healthcheck(macro: str, macro_id: str):
    if macro not in app.state.hosts[0].macros.keys():
        raise HTTPException(status_code=404, detail=f"Macro {macro} not found")

    selected_hosts = [host.node_healthy for host in app.state.hosts if host.macros[macro] == macro_id]

    logger.info(app.state.hosts[0].last_check)

    if not selected_hosts:
        raise HTTPException(status_code=404, detail=f"No hosts with {macro}={macro_id} found")

    if any(selected_hosts):
        return 200, "Ok."
    else:
        raise HTTPException(status_code=500, detail=f"{macro_id} is unhealthy")


@app.on_event("startup")
async def start_up():
    instrumentator.expose(app)
    asyncio.create_task(run_loop())


async def run_loop():
    config = ExporterConfig()
    app.state.hosts = await load_hosts(config)  # Needs to be called from main event loop since pydantic is sync
    collectors = [MetricsGroupCollector(REGISTRY, config, metric) for metric in config.metrics]

    async with TaskGroup() as tg:
        await setup_healthchecks(app.state.hosts, REGISTRY, tg)
        for host in app.state.hosts:
            hostname = host.name
            for collector in collectors:
                if collector.specific_host and collector.specific_host != hostname:
                    continue
                logger.info(f"Adding collectors for {collector.metric_names} on host {hostname}")
                tg.create_task(collector.collect(host))


async def setup_healthchecks(hosts: List[Host], registry: CollectorRegistry, tg: TaskGroup):
    labels = DEFAULT_LABELS + hosts[0].macro_keys
    logger.info(f"Adding healthcheck prom metric with labels {labels}")
    clickhouse_health = Enum(
        PREFIX + "_node_health",
        "Clickhouse Nodes Health Status",
        states=["healthy", "unhealthy"],
        labelnames=labels,
        registry=registry

    )
    logger.info(f"Adding replication check prom metric {labels}")
    clickhouse_replication_health = Enum(
        PREFIX + "_replication_status",
        "Clickhouse Nodes Replication Status",
        states=["healthy", "unhealthy"],
        labelnames=labels,
        registry=registry
    )
    for host in hosts:
        logger.info("Adding health probes")
        tg.create_task(healthcheck(host, clickhouse_health, clickhouse_replication_health))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
