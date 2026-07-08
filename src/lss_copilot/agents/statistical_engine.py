"""C. Statistical Engine Agent (LOW tier / high-precision execution).

Hallucination is designed out, not prompted away:
  - the library of tests lives in `lss_copilot.stats` as deterministic code,
  - the LOW-tier LLM's only job is *planning* which tests to run (it emits an
    `AnalysisPlan` naming library calls + columns — never numbers),
  - custom analyses beyond the library are executed in the AST-checked,
    rlimited sandbox (`tools.sandbox`), and only the sandbox's JSON output
    enters the state. Every number in a `StatisticalFinding` comes from
    NumPy/SciPy, never from a model.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, RootModel

from lss_copilot.config import ModelTier, settings
from lss_copilot.agents.base import SubAgent
from lss_copilot.stats import (
    capability_analysis,
    describe,
    ols_regression,
    pareto_analysis,
    run_hypothesis_test,
)
from lss_copilot.state.schemas import (
    AgentName,
    DataSourceRef,
    DMAICPhase,
    HandoffEnvelope,
    LSSProjectState,
    StatisticalFinding,
)
from lss_copilot.tools.artifact_store import ArtifactStore
from lss_copilot.tools.sandbox import run_in_sandbox


class PlannedTest(BaseModel):
    kind: Literal["describe", "capability", "hypothesis", "regression", "pareto", "custom"]
    target_metric: str = Field(description="numeric column being explained (the Y)")
    group_by: str = ""
    factors: list[str] = Field(default_factory=list, description="X columns for regression")
    lsl: float | None = None
    usl: float | None = None
    custom_code: str = Field(default="", description="sandbox code for kind=custom")
    rationale: str = ""


class AnalysisPlan(RootModel[list[PlannedTest]]):
    pass


class StatisticalFindings(RootModel[list[StatisticalFinding]]):
    pass


class StatisticalEngineAgent(SubAgent):
    name = AgentName.STATISTICAL_ENGINE
    tier = ModelTier.LOW
    system_prompt = (
        "You plan statistical analyses for a Six Sigma project. Given a dataset "
        "schema and a question, emit a list of tests to run from the library: "
        "describe, capability, hypothesis (grouped comparison), regression, "
        "pareto, or custom sandbox code. Choose columns that exist. Never "
        "invent numeric results — you only plan; code executes."
    )

    def __init__(self, store: ArtifactStore, llm=None) -> None:
        super().__init__(llm)
        self.store = store

    def run(
        self,
        state: LSSProjectState,
        brief: str,
        dataset: DataSourceRef | None = None,
        plan: list[PlannedTest] | None = None,
    ) -> HandoffEnvelope:
        # Prefer the per-case feature table: that's where the Y and the X's live.
        baseline = state.baseline
        ref = dataset \
            or (baseline.feature_table if baseline else None) \
            or (baseline.dataset if baseline else None) \
            or next(iter(state.datasets.values()), None)
        if ref is None:
            raise ValueError("statistical engine requires a dataset reference")
        df = self.store.get_dataframe(ref)

        usage = None
        if plan is None:
            schema_desc = ", ".join(f"{c} ({t})" for c, t in df.dtypes.items())
            planned, usage = self._ask(
                f"Question: {brief}\nDataset columns: {schema_desc}\nRows: {len(df)}",
                AnalysisPlan,
            )
            plan = planned.root

        findings: list[StatisticalFinding] = []
        for test in plan:
            try:
                findings.extend(self._execute(test, df))
            except (ValueError, KeyError) as exc:
                # A bad plan step is recorded, never silently invented.
                findings.append(StatisticalFinding(
                    test_name=f"{test.kind}_failed",
                    target_metric=test.target_metric,
                    statistic=0.0, p_value=1.0, significant=False,
                    details={"error": str(exc)},
                ))
        return self._envelope(
            DMAICPhase.ANALYZE, StatisticalFindings(findings), usage,
            notes=f"Executed {len(plan)} planned tests deterministically",
        )

    def _execute(self, test: PlannedTest, df: pd.DataFrame) -> list[StatisticalFinding]:
        if test.kind == "describe":
            stats = describe(df[test.target_metric].dropna().tolist())
            return [StatisticalFinding(
                test_name="descriptive", target_metric=test.target_metric,
                statistic=stats["mean"], p_value=1.0, significant=False, details=stats,
            )]
        if test.kind == "capability":
            result = capability_analysis(
                df[test.target_metric].dropna().tolist(), lsl=test.lsl, usl=test.usl
            )
            cpk = result["cpk"]
            return [StatisticalFinding(
                test_name="capability", target_metric=test.target_metric,
                statistic=float(cpk if cpk is not None else 0.0), p_value=1.0,
                significant=bool(cpk is not None and cpk < 1.33),  # flags incapable process
                details={k: v for k, v in result.items()},
            )]
        if test.kind == "hypothesis":
            groups = {
                str(name): grp[test.target_metric].dropna().tolist()
                for name, grp in df.groupby(test.group_by)
            }
            return [run_hypothesis_test(test.target_metric, groups=groups)]
        if test.kind == "regression":
            cols = [test.target_metric, *test.factors]
            clean = df[cols].dropna()
            X: dict[str, list[float]] = {}
            for f in test.factors:
                col = clean[f]
                if pd.api.types.is_numeric_dtype(col) or pd.api.types.is_bool_dtype(col):
                    X[f] = col.astype(float).tolist()
                else:  # categorical factor: one-hot encode (drop first level)
                    dummies = pd.get_dummies(col.astype(str), prefix=f, drop_first=True)
                    for dcol in dummies.columns:
                        X[dcol] = dummies[dcol].astype(float).tolist()
            return [ols_regression(
                test.target_metric, clean[test.target_metric].astype(float).tolist(), X,
            )]
        if test.kind == "pareto":
            counts = df.groupby(test.group_by)[test.target_metric].sum().to_dict() \
                if test.target_metric in df.columns \
                else df[test.group_by].value_counts().to_dict()
            result = pareto_analysis({str(k): float(v) for k, v in counts.items()})
            vital = result["vital_few"]
            return [StatisticalFinding(
                test_name="pareto", target_metric=test.target_metric or test.group_by,
                factors=list(vital), statistic=float(len(vital)), p_value=1.0,
                significant=True, details=result,
            )]
        if test.kind == "custom":
            sample = df.head(10_000)  # bound sandbox payload
            sbx = run_in_sandbox(
                test.custom_code,
                input_data={"records": sample.to_dict(orient="records")},
                timeout_seconds=settings.sandbox_timeout_seconds,
                memory_mb=settings.sandbox_memory_mb,
            )
            if not sbx.ok:
                raise ValueError(f"sandbox failed: {sbx.stderr or sbx.stdout}")
            out = sbx.result if isinstance(sbx.result, dict) else {"result": sbx.result}
            return [StatisticalFinding(
                test_name="custom_sandbox", target_metric=test.target_metric,
                statistic=float(out.get("statistic", 0.0)),
                p_value=float(out.get("p_value", 1.0)),
                significant=bool(out.get("significant", False)),
                details=out,
            )]
        raise ValueError(f"unknown test kind: {test.kind}")
