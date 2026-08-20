import pytest

from sre_lab.chaosmesh import ChaosMeshAdapter, ChaosMeshError
from sre_lab.scenario import Scenario


class FakeChaosClient:
    def __init__(self):
        self.calls = []

    def apply(self, manifest): self.calls.append(("apply", manifest))
    def get(self, name, namespace): self.calls.append(("get", name, namespace)); return {"state": "running"}
    def delete(self, name, namespace): self.calls.append(("delete", name, namespace))


def scenario():
    return Scenario.from_dict({
        "problem_id": "http-5xx", "source_case_id": "t001", "reproduction_level": "behavioral",
        "fault_type": "httpError5xx", "target": "payment", "workload": {"namespace": "chaos-lab"},
        "injector": {"type": "chaos-mesh", "mode": "pod-kill", "duration_seconds": 120}, "steady_state": [],
        "symptom_contract": [], "stop_conditions": [], "cleanup": {"ttl_seconds": 180}, "grading": {},
    })


def test_adapter_is_namespace_scoped_and_reversible():
    client = FakeChaosClient(); adapter = ChaosMeshAdapter(client)
    exp = adapter.create(scenario(), run_id="run-123456789")
    assert exp.manifest["kind"] == "PodChaos"
    assert exp.namespace == "chaos-lab"
    assert exp.manifest["spec"]["selector"]["labelSelectors"] == {"app": "payment"}
    adapter.status(exp); adapter.cleanup(exp)
    assert [call[0] for call in client.calls] == ["apply", "get", "delete"]


def test_adapter_rejects_other_namespace():
    data = scenario().__dict__
    data["workload"] = {"namespace": "default"}
    with pytest.raises(ChaosMeshError, match="namespace"):
        ChaosMeshAdapter(FakeChaosClient()).manifest(Scenario(**data), run_id="run-1")


def test_adapter_rejects_privileged_network_mode_by_default():
    data = scenario().__dict__
    data["injector"] = {"type": "chaos-mesh", "mode": "network-delay", "latency_ms": 100}
    with pytest.raises(ChaosMeshError, match="privileged"):
        ChaosMeshAdapter(FakeChaosClient()).manifest(Scenario(**data), run_id="run-1")
