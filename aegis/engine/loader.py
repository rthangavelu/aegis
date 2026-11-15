"""YAML loader and schema validator for test cases, remediations and AI systems."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

_SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((_SCHEMAS_DIR / name).read_text())


def load_yaml(path: Path) -> Any:
    with open(path) as fh:
        return yaml.safe_load(fh)


def validate_test_case(data: dict[str, Any], source: str = "") -> None:
    schema = _load_schema("test_case.schema.json")
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        loc = f" in {source}" if source else ""
        raise ValueError(f"Invalid test case{loc}: {exc.message}") from exc


def validate_remediation(data: dict[str, Any], source: str = "") -> None:
    schema = _load_schema("remediation.schema.json")
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        loc = f" in {source}" if source else ""
        raise ValueError(f"Invalid remediation{loc}: {exc.message}") from exc


def validate_system(data: dict[str, Any], source: str = "") -> None:
    schema = _load_schema("system.schema.json")
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        loc = f" in {source}" if source else ""
        raise ValueError(f"Invalid system{loc}: {exc.message}") from exc


def load_test_library(testlib_dir: Path) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    for yaml_file in sorted(testlib_dir.rglob("*.yaml")):
        data = load_yaml(yaml_file)
        validate_test_case(data, str(yaml_file))
        data["_source"] = str(yaml_file)
        tests.append(data)
    return tests


def load_remediations(remediation_dir: Path) -> list[dict[str, Any]]:
    remediations: list[dict[str, Any]] = []
    for yaml_file in sorted(remediation_dir.rglob("*.yaml")):
        data = load_yaml(yaml_file)
        validate_remediation(data, str(yaml_file))
        data["_source"] = str(yaml_file)
        remediations.append(data)
    return remediations


def load_systems(systems_yaml: Path) -> list[dict[str, Any]]:
    raw = load_yaml(systems_yaml)
    systems = raw.get("systems", [])
    for system in systems:
        validate_system(system, str(systems_yaml))
    return systems
