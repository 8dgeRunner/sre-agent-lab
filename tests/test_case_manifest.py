import json
from pathlib import Path


def test_rca100_manifest_is_fixed_stratified_and_has_no_chaosblade():
    manifest = json.loads(Path("manifests/rca100-v1.1-12.json").read_text())
    cases = manifest["cases"]
    assert manifest["version"] == "v1.1"
    assert len(cases) == 12
    assert len({item["task_id"] for item in cases}) == 12
    assert len({item["fault_type"] for item in cases}) == 12
    assert all(item["injector"] in {"chaos-mesh", "kubernetes-api", "fault-service"} for item in cases)
    assert all(item["live_status"] in {"implemented", "candidate", "offline-only"} for item in cases)
