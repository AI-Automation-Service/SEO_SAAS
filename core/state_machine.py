"""
Project State Machine.

States: SETUP → CLUSTERED → PLANNED → ACTIVE → MONITORING
Transitions are triggered by key events and update project.yaml.
Agents warn if project state is below PLANNED (no execution plan yet).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.context import ProjectContext

_STATE_ORDER = ["SETUP", "CLUSTERED", "PLANNED", "ACTIVE", "MONITORING"]


def _state_rank(state: str) -> int:
    try:
        return _STATE_ORDER.index(state.upper())
    except ValueError:
        return 0


def advance_state(ctx: "ProjectContext", target: str) -> bool:
    """
    Advance project state to `target` if it is higher than current.
    Returns True if state changed, False if already at or beyond target.
    """
    current_rank = _state_rank(ctx.config.project_state)
    target_rank = _state_rank(target)

    if target_rank <= current_rank:
        return False

    from core.project_writer import update_project_yaml
    config_file = ctx.project_dir / "config" / "project.yaml"
    update_project_yaml(config_file, {"project_state": target.upper()})
    ctx.config.project_state = target.upper()
    return True


def check_state_warning(ctx: "ProjectContext", required: str) -> str | None:
    """
    Return a warning string if the project state is below `required`, else None.
    Used by action agents before executing.
    """
    if _state_rank(ctx.config.project_state) < _state_rank(required):
        return (
            f"Warning: Project is in state '{ctx.config.project_state}'. "
            f"'{required}' state or higher is recommended before running this agent. "
            "Run seo-cluster (Keywords tab) and seo-plan (Strategy tab) first for best results."
        )
    return None
