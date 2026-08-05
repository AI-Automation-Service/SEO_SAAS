"""
contracts — Output contracts for all SEO OS AI agents.

Each module defines the Pydantic response model for one agent.
Use model_validate_json() in routers — never bare json.loads().

Usage:
    from contracts.meta import MetaResponse
    response = MetaResponse.model_validate_json(raw_string)

Add new imports here as contracts are created during Phase 2 migration.
"""
from contracts.meta import MetaResponse

__all__ = [
    "MetaResponse",
]
