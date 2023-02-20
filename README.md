<h1 align="center"><code>ch_exporter</code></h1>

`ch_exporter` is a simple and configurable alternative to the official (unmaintained) [clickhouse_exporter](https://github.com/ClickHouse/clickhouse_exporter).
It provides an easy way to extend the metrics provided by Clickhouse out of the box with metrics based on any queryable table.

## Example
```
groups:
  - metrics:
      - name: <metric_1>
        description: Nice name
        metric: <Gauge|Summary|Bucket|Counter>
        observation: <observation_1>
      - name: <metric_2>
        description: Nice name
        metric: <Gauge|Summary|Bucket|Counter>
        observation: <observation_2>
    labels:
      - label_1
      - label_2
    query:
      select 
        label_1, 
        label_2, 
        sum(metric) as metric_1, 
        count() as metric_2
      from database.table
      group by label_1, label_2
```
