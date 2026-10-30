"""CI acceptance: every integration module exceeds 95% executed statements."""
import json
from pathlib import Path

report = json.loads(Path("coverage.json").read_text())
failed = []
for name, result in report["files"].items():
    summary = result["summary"]
    count = summary["num_statements"]
    if count and summary["covered_lines"] / count <= 0.95:
        failed.append(name)
if failed:
    raise SystemExit("Modules must exceed 95% statement coverage: " + ", ".join(failed))
flow = report["files"]["custom_components/flame_connect/config_flow.py"]["summary"]
if flow["missing_lines"] or flow.get("missing_branches", 0):
    raise SystemExit("Config flow must have 100% line and branch coverage")
print("All modules exceed 95%; config flow is fully covered.")
