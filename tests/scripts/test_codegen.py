import importlib.util, pathlib
from typing import Optional, List

_p = pathlib.Path(__file__).resolve().parents[2] / "scripts/codegen/gen_schema.py"
_s = importlib.util.spec_from_file_location("gen_schema", _p)
gen = importlib.util.module_from_spec(_s)
_s.loader.exec_module(gen)
from core.metadata import SourceConfig


def test_sql_type():
    assert gen.sql_type(Optional[str]) == "STRING"
    assert gen.sql_type(List[str]) == "ARRAY<STRING>"
    assert gen.sql_type(bool) == "BOOLEAN"


def test_model_to_ddl():
    ddl = gen.model_to_ddl(SourceConfig)
    assert "cfg_source" in ddl and "PRIMARY KEY (source_id)" in ddl and "USING DELTA" in ddl
