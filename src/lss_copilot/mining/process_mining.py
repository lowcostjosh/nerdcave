"""Process mining over standardized event logs.

Input contract (produced by the Data Intake agent): a pandas DataFrame with
columns `case_id`, `activity`, `timestamp` (tz-aware). From that we
reconstruct the as-is flow: variants, transition frequencies/durations,
rework loops, bottlenecks, PCE, and a Mermaid.js diagram for humans.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

import pandas as pd

REQUIRED_COLUMNS = {"case_id", "activity", "timestamp"}


def _mermaid_label(text: str) -> str:
    """Quotes and HTML-ish characters break Mermaid node/edge labels."""
    return (text.replace('"', "'")
                .replace("<", "(").replace(">", ")")
                .replace("[", "(").replace("]", ")")
                .replace("{", "(").replace("}", ")"))


@dataclass
class ProcessModel:
    activities: list[str]
    transition_counts: dict[tuple[str, str], int]
    transition_mean_hours: dict[tuple[str, str], float]
    variants: Counter[tuple[str, ...]] = field(default_factory=Counter)
    rework_loops: list[tuple[str, str]] = field(default_factory=list)
    bottlenecks: list[tuple[str, str]] = field(default_factory=list)
    mean_cycle_time_hours: float = 0.0
    median_cycle_time_hours: float = 0.0

    def to_mermaid(self, max_edges: int = 40) -> str:
        """Directly-follows graph as Mermaid flowchart; bottlenecks highlighted."""
        ids = {a: f"n{i}" for i, a in enumerate(self.activities)}
        lines = ["flowchart LR"]
        for a in self.activities:
            lines.append(f'    {ids[a]}["{_mermaid_label(a)}"]')
        top = sorted(self.transition_counts.items(), key=lambda kv: kv[1], reverse=True)
        rendered = [edge for edge, _ in top[:max_edges]]
        # Bottlenecks must be visible even when rare (slow-but-infrequent edges).
        for edge in self.bottlenecks:
            if edge not in rendered and edge in self.transition_counts:
                rendered.append(edge)
        for src, dst in rendered:
            count = self.transition_counts[(src, dst)]
            hours = self.transition_mean_hours.get((src, dst), 0.0)
            lines.append(f'    {ids[src]} -->|"{count}x, {hours:.1f}h"| {ids[dst]}')
        for edge in self.bottlenecks:
            if edge in rendered:
                lines.append(f"    linkStyle {rendered.index(edge)} "
                             "stroke:#d62728,stroke-width:3px")
        return "\n".join(lines)


def mine_process(events: pd.DataFrame, bottleneck_top_n: int = 3) -> ProcessModel:
    missing = REQUIRED_COLUMNS - set(events.columns)
    if missing:
        raise ValueError(f"event log missing columns: {sorted(missing)}")

    df = events.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values(["case_id", "timestamp"])

    transition_counts: Counter[tuple[str, str]] = Counter()
    durations: dict[tuple[str, str], list[float]] = defaultdict(list)
    variants: Counter[tuple[str, ...]] = Counter()
    cycle_times: list[float] = []
    revisit_edges: set[tuple[str, str]] = set()

    for _, case in df.groupby("case_id", sort=False):
        acts = case["activity"].tolist()
        times = case["timestamp"].tolist()
        variants[tuple(acts)] += 1
        cycle_times.append((times[-1] - times[0]).total_seconds() / 3600)
        seen: set[str] = {acts[0]}
        for (a, t1), (b, t2) in zip(zip(acts, times), zip(acts[1:], times[1:])):
            transition_counts[(a, b)] += 1
            durations[(a, b)].append((t2 - t1).total_seconds() / 3600)
            if b in seen:  # re-entering an earlier state = rework, even via intermediates
                revisit_edges.add((a, b))
            seen.add(b)

    transition_mean = {k: sum(v) / len(v) for k, v in durations.items()}
    rework = list(revisit_edges)
    # Bottleneck = slowest transitions weighted by how often they occur
    weighted = sorted(
        transition_mean.items(),
        key=lambda kv: kv[1] * transition_counts[kv[0]],
        reverse=True,
    )
    activities = list(dict.fromkeys(df["activity"].tolist()))
    cycles = pd.Series(cycle_times) if cycle_times else pd.Series([0.0])

    return ProcessModel(
        activities=activities,
        transition_counts=dict(transition_counts),
        transition_mean_hours=transition_mean,
        variants=variants,
        rework_loops=sorted(set(rework)),
        bottlenecks=[k for k, _ in weighted[:bottleneck_top_n]],
        mean_cycle_time_hours=float(cycles.mean()),
        median_cycle_time_hours=float(cycles.median()),
    )


def process_cycle_efficiency(value_add_hours: float, total_lead_hours: float) -> float:
    """PCE = value-add time / total lead time (clamped to [0, 1])."""
    if total_lead_hours <= 0:
        raise ValueError("total lead time must be positive")
    if value_add_hours < 0:
        raise ValueError("value-add time cannot be negative")
    return min(value_add_hours / total_lead_hours, 1.0)
