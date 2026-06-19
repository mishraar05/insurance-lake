"""Structural tests for core.contracts."""
from core.contracts import (
    Reader, LoadStrategy, Engine, Check, CheckResult, Masker, RunContext, RunResult,
)
from core.metadata import MaskingRuleConfig


def test_checkresult_dataclass():
    r = CheckResult(rule_id="dq1", passed=True, failed_count=0, action="WARN")
    assert r.passed and r.action == "WARN"


def test_runcontext_runresult():
    ctx = RunContext(component="ingestion", entity="policy", run_type="BATCH_INCREMENTAL")
    res = RunResult(status="SUCCESS", metrics={"rows_written": 10})
    assert ctx.entity == "policy" and res.status == "SUCCESS" and res.run_id is None


def test_masking_rule_config():
    m = MaskingRuleConfig(masking_rule_id="m1", rule_name="mask_ssn", target_id="t1",
                          column_name="ssn", classification="RESTRICTED", technique="HASH")
    assert m.technique == "HASH" and m.reversible_flag is False


def test_runtime_checkable_masker():
    class DummyMasker:
        def mask(self, df, rules):
            return df
    assert isinstance(DummyMasker(), Masker)


def test_all_protocols_importable():
    assert all(p is not None for p in (Reader, LoadStrategy, Engine, Check, Masker))
