"""Streamlit dashboard over a checkpointed LSS project state.

Run:  streamlit run src/lss_copilot/dashboard/streamlit_app.py -- --state state.json

Reads a serialized `LSSProjectState` (the graph checkpointer can export one at
any tollgate) and renders each DMAIC phase's artifacts, including the Mermaid
VSM and the live SPC panel.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

from lss_copilot.state.schemas import LSSProjectState


def _load_state() -> LSSProjectState | None:
    args = sys.argv
    path = Path(args[args.index("--state") + 1]) if "--state" in args else Path("state.json")
    if not path.exists():
        return None
    return LSSProjectState.model_validate(json.loads(path.read_text()))


def main() -> None:
    st.set_page_config(page_title="LSS Co-Pilot", layout="wide")
    state = _load_state()
    if state is None:
        st.warning("No project state found. Pass --state <file.json>.")
        return

    st.title(f"LSS Co-Pilot — {state.project_id}")
    st.caption(f"Phase: {state.phase.value.upper()} · "
               f"LLM tokens spent: {state.ledger.total:,}")

    tabs = st.tabs(["Define", "Measure", "Analyze", "Improve", "Control", "Spend"])

    with tabs[0]:
        if state.charter:
            st.subheader(state.charter.title)
            st.markdown(f"**Problem** — {state.charter.problem_statement}")
            st.markdown(f"**Goal** — {state.charter.goal_statement}")
            c1, c2 = st.columns(2)
            c1.markdown("**In scope**\n" + "\n".join(f"- {s}" for s in state.charter.in_scope))
            c2.markdown("**Out of scope**\n" + "\n".join(f"- {s}" for s in state.charter.out_of_scope))
            st.json(state.charter.sipoc.model_dump())

    with tabs[1]:
        if state.baseline:
            b = state.baseline
            c = st.columns(4)
            c[0].metric("Mean cycle time (h)", f"{b.mean_cycle_time_hours:.1f}")
            c[1].metric("Defect rate", f"{b.defect_rate:.1%}")
            c[2].metric("Throughput /day", f"{b.throughput_per_day:.1f}")
            c[3].metric("PCE", f"{b.process_cycle_efficiency:.1%}")
            st.markdown("**Value stream map**")
            st.code(b.value_stream_mermaid, language="mermaid")
            st.markdown("**Bottlenecks**\n" + "\n".join(f"- {x}" for x in b.bottlenecks))

    with tabs[2]:
        for rc in state.root_causes:
            with st.expander(f"Root cause ({rc.confidence:.0%}): {rc.description}"):
                for f in rc.supporting_findings:
                    st.write(f"`{f.test_name}` on **{f.target_metric}**: "
                             f"stat={f.statistic:.3f}, p={f.p_value:.4f}")
                for e in rc.fmea_entries:
                    st.write(f"FMEA · {e.failure_mode} → RPN **{e.rpn}**")
        if state.fishbone:
            st.code(state.fishbone.to_mermaid(), language="mermaid")

    with tabs[3]:
        for bp in state.blueprints:
            with st.expander(f"[{bp.kind}] {bp.title}"):
                st.markdown(bp.summary)
                if bp.code:
                    st.code(bp.code)
                st.markdown("**Rollout**\n" + "\n".join(f"1. {s}" for s in bp.rollout_steps))

    with tabs[4]:
        if state.control_plan:
            cp = state.control_plan
            for m in cp.monitored_metrics:
                st.write(f"**{m}** · CL={cp.center_line[m]:.2f} "
                         f"UCL={cp.ucl[m]:.2f} LCL={cp.lcl[m]:.2f}")
            if cp.alerts:
                st.error(f"{len(cp.alerts)} active SPC alerts")
                st.dataframe([a.model_dump() for a in cp.alerts])
            else:
                st.success("Process in control")

    with tabs[5]:
        st.bar_chart(state.ledger.by_agent)


if __name__ == "__main__":
    main()
