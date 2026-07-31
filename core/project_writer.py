import yaml
from pathlib import Path


def update_project_yaml(config_file: Path, updates: dict) -> None:
    """Deep-merge `updates` into the existing project.yaml and write it back."""
    current = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    _deep_merge(current, updates)
    config_file.write_text(
        yaml.dump(current, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _deep_merge(base: dict, updates: dict) -> None:
    for key, value in updates.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
