"""Export the external-agent contract without custom JSON processing."""

from murdoku.dsl.expressions import ConstraintSet


def schema_json() -> str:
    import json

    return json.dumps(ConstraintSet.model_json_schema(), indent=2)
