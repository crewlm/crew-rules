from pathlib import Path

import json
from classes.rule import AnyRule

FILES_DIR = Path(__file__).resolve().parent / ".files"


def test_docs_schema_01():
    # Generate JSON schema directly from Pydantic
    schema = AnyRule.json_schema()

    fpath = FILES_DIR / "anyrule_schema.json"
    with open(fpath, "w") as f:
        json.dump(schema, f, indent=4)
