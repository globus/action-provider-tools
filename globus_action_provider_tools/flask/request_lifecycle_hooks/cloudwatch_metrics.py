from __future__ import annotations

import json
import logging
import time
import typing as t
from datetime import datetime

from flask import Response, g

log = logging.getLogger("globus_action_provider_tools.cloudwatch_metric_emf_logger")


class CloudWatchMetricEMFLogger:
    """
    Flask RequestLifecycleHooks to emit CloudWatch Metrics detailing action provider
      usage via the CloudWatch EMF Format.
    https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Specification.html

    Metric Structure
    ================

    Aggregate
    ---------
      Namespace: {supplied_namespace}
      Dimensions:
        ActionProvider: {supplied_action_provider_name}

    Route-Specific
    --------------
      Namespace: {supplied_namespace}
      Dimensions:
        ActionProvider: {supplied_action_provider_name}
        Route: "run" | "resume" | "status" | ...

    Included Metrics:
     * Count - The total number API requests in a given period.
     * 2XXs - The number of successful responses returned in a given period.
     * 4XXs - The number of client-side errors captured in a given period.
     * 5XXs - The number of server-side errors captured in a given period.
     * RequestLatency - The number of milliseconds between the request being received
        and the response being sent.
    """

    def __init__(
        self, namespace: str, action_provider_name: str, log_level: int | None = None
    ):
        """
        :param namespace: Custom CloudWatch Namespace target
        :param action_provider_name: Action Provider Name to be used in metric dimension
           sets
        :param log_level: Optional log level to use when emitting metrics. If None,
           metrics will be printed to stdout instead of logged.
        """
        self._namespace = namespace
        self._action_provider_name = action_provider_name
        self._log_level = log_level

    def before_request(self):
        g.request_start_perf_counter_ms = time.perf_counter() * 1000

    def after_request(self, response: Response):
        if hasattr(g, "route_type") and hasattr(g, "request_start_perf_counter_ms"):
            request_latency_ms = (
                time.perf_counter() * 1000 - g.request_start_perf_counter_ms
            )
            self.emit_route_metrics(
                route_name=g.route_type,
                request_latency_ms=request_latency_ms,
                response_status=response.status_code,
            )
        return response

    def teardown_request(self, error: BaseException | None):
        # If a request errors mid-handling, after_request handlers will not be called,
        #   so we need to emit metrics for errors separately here
        if error:
            if hasattr(g, "route_type") and hasattr(g, "request_start_time"):
                status_code = 500
                if hasattr(error, "code"):
                    status_code = error.code
                request_latency_ms = (
                    time.perf_counter() * 1000 - g.request_start_perf_counter_ms
                )
                self.emit_route_metrics(
                    route_name=g.route_type,
                    request_latency_ms=request_latency_ms,
                    response_status=status_code,
                )
            raise error

    def emit_route_metrics(
        self,
        route_name: str,
        request_latency_ms: float,
        response_status: int,
    ):
        emf_obj = _to_emf(
            namespace=self._namespace,
            dimension_sets=[
                {"ActionProvider": self._action_provider_name},
                {"ActionProvider": self._action_provider_name, "Route": route_name},
            ],
            metrics=[
                ("RequestCount", 1, "Count"),
                ("2XXs", 1 if 200 <= response_status < 300 else 0, "Count"),
                ("4XXs", 1 if 400 <= response_status < 500 else 0, "Count"),
                ("5XXs", 1 if 500 <= response_status < 600 else 0, "Count"),
                ("RequestLatency", request_latency_ms, "Milliseconds"),
            ],
        )

        serialized_emf = json.dumps(emf_obj)
        if not self._log_level:
            print(serialized_emf)
        else:
            log.log(self._log_level, serialized_emf)


# fmt: off
# https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricDatum.html
CloudWatchUnit = t.Literal[
    "Seconds", "Microseconds", "Milliseconds", "Bytes", "Kilobytes", "Megabytes",
    "Gigabytes", "Terabytes", "Bits", "Kilobits", "Megabits", "Gigabits", "Terabits",
    "Percent", "Count", "Bytes/Second", "Kilobytes/Second", "Megabytes/Second",
    "Gigabytes/Second", "Terabytes/Second", "Bits/Second", "Kilobits/Second",
    "Megabits/Second", "Gigabits/Second", "Terabits/Second", "Count/Second", "None"
]
# fmt: on


def _to_emf(
    namespace: str,
    dimension_sets: list[dict[str, str]],
    metrics: list[tuple[str, str | int | float, CloudWatchUnit | None]],
    timestamp: datetime | None = None,
) -> dict[str, t.Any]:
    """
    Mutates a list of metrics into CloudWatch Embedded Metric Format
    https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Specification.html

    This results in an object like
    ```json
    {
        "_aws": {
            "Timestamp": 1680634571444,
            "CloudWatchMetrics": [{
                "Namespace": "MyCoolNamespace",
                "Dimensions": [["Foo"], ["Foo", "Bar"]],
                "Metrics": [{ "Name": "MyCoolMetric", "Unit": "Milliseconds" }]
            }]
        },
        "Foo": "a",
        "Bar": "b",
        "MyCoolMetric": 37,
    }
    ```
    Note how there are three additional top-level keys besides "_aws".
    This is because Dimension Values & Metric Values must be referenced not passed
        explicitly

    :namespace str: Namespace
    :metric_name str: Metric Name
    :dimension_sets list[dict[str, str]]: A collection of Dimension Sets (each metric
        will be emitted with each dimension set)
    :metrics list[tuple[str, str | int | float, str | None]]: Metric Tuple in the format
        (metric_name, value, Optional[unit])
    :timestamp datetime | None: Timestamp to use for the metric. If None, the current
        time will be used.
    :returns: An emf formatted dict
    """
    timestamp = timestamp or datetime.now()
    epoch_ms = int(timestamp.timestamp() * 1000)
    _verify_no_emf_root_collisions(
        {metric_name for metric_name, _, _ in metrics}, dimension_sets
    )

    emf_obj: t.Dict[str, t.Any] = {}

    emf_metrics = []
    for metric_name, value, unit in metrics:
        emf_obj[metric_name] = value
        emf_metric = {"Name": metric_name}
        if unit is not None:
            emf_metric["Unit"] = unit
        emf_metrics.append(emf_metric)

    emf_dimension_sets = []
    for dimension_map in dimension_sets:
        for dimension_name, dimension_value in dimension_map.items():
            emf_obj[dimension_name] = dimension_value
        emf_dimension_sets.append(list(dimension_map.keys()))

    emf_obj["_aws"] = {
        "Timestamp": epoch_ms,
        "CloudWatchMetrics": [
            {
                "Namespace": namespace,
                "Dimensions": emf_dimension_sets,
                "Metrics": emf_metrics,
            }
        ],
    }

    return emf_obj


def _verify_no_emf_root_collisions(
    metric_names: set[str], dimension_sets: list[dict[str, str]]
):
    """
    Verify that there are no disallowed collisions between the root keys of the emf
       object

    :raises: RuntimeError if names/values collide in ways that preclude them from
       being emitted via EMF
    """
    # Verify that no dimension names match any metric names
    dimension_names = {
        dimension_name
        for dimension_map in dimension_sets
        for dimension_name in dimension_map.keys()
    }

    namespace_collisions = metric_names.intersection(dimension_names)
    if namespace_collisions:
        raise RuntimeError(
            f"Cannot overlap dimension names and metric names ({namespace_collisions})"
        )

    # Verify that no dimension names in different dimension sets conflict
    dimension_values: t.Dict[str, t.Set[str]] = {}
    for dimension_map in dimension_sets:
        for dimension_name, dimension_value in dimension_map.items():
            dimension_values.setdefault(dimension_name, set()).add(dimension_value)
    dimension_collisions = {
        dimension_name
        for dimension_name, dimension_value in dimension_values.items()
        if len(dimension_value) > 1
    }
    if dimension_collisions:
        raise RuntimeError(
            f"Dimension sets with the same name must have the same value "
            f"({dimension_collisions})"
        )
