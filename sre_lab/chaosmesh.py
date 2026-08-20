from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from .scenario import Scenario


class ChaosMeshClient(Protocol):
    def apply(self, manifest: dict[str, Any]) -> Any: ...
    def get(self, name: str, namespace: str) -> Any: ...
    def delete(self, name: str, namespace: str) -> Any: ...


class ChaosMeshError(RuntimeError):
    pass


@dataclass
class ChaosExperiment:
    name: str
    namespace: str
    manifest: dict[str, Any]


class ChaosMeshAdapter:
    """Builds namespace-scoped manifests; execution is delegated to a locked client."""

    def __init__(self, client: ChaosMeshClient, *, allow_privileged_modes: bool = False):
        self.client = client
        self.allow_privileged_modes = allow_privileged_modes

    def manifest(self, scenario: Scenario, *, run_id: str) -> dict[str, Any]:
        if scenario.injector_type != "chaos-mesh":
            raise ChaosMeshError("scenario is not a Chaos Mesh scenario")
        namespace = str(scenario.workload.get("namespace", "chaos-lab"))
        if namespace != "chaos-lab":
            raise ChaosMeshError("Chaos Mesh target namespace is fixed to chaos-lab")
        name = f"{scenario.problem_id}-{run_id[:8]}".lower().replace("_", "-")
        duration = max(1, int(scenario.injector.get("duration_seconds", 60)))
        mode = scenario.injector.get("mode", "network")
        if mode == "network-delay":
            if not self.allow_privileged_modes:
                raise ChaosMeshError("network-delay requires an explicitly approved privileged Chaos Mesh daemon")
            spec = {"mode": "all", "selector": {"namespaces": [namespace],
                    "labelSelectors": {"app": scenario.target}},
                    "action": "delay", "delay": {"latency": f"{int(scenario.injector.get('latency_ms', 100))}ms"},
                    "duration": f"{duration}s"}
            kind = "NetworkChaos"
        elif mode == "pod-kill":
            spec = {"mode": "all", "selector": {"namespaces": [namespace],
                    "labelSelectors": {"app": scenario.target}},
                    "action": "pod-kill", "duration": f"{duration}s"}
            kind = "PodChaos"
        else:
            raise ChaosMeshError("unsupported Chaos Mesh mode")
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1", "kind": kind,
            "metadata": {"name": name, "namespace": namespace,
                          "labels": {"lab.run_id": run_id, "lab.reproduction": "behavioral"}},
            "spec": spec,
        }

    def create(self, scenario: Scenario, *, run_id: str) -> ChaosExperiment:
        manifest = self.manifest(scenario, run_id=run_id)
        self.client.apply(manifest)
        return ChaosExperiment(manifest["metadata"]["name"], manifest["metadata"]["namespace"], manifest)

    def status(self, experiment: ChaosExperiment) -> Any:
        return self.client.get(experiment.name, experiment.namespace)

    def cleanup(self, experiment: ChaosExperiment) -> None:
        self.client.delete(experiment.name, experiment.namespace)
