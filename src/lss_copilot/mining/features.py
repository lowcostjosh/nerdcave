"""Case-level feature table: the bridge from event logs to root-cause statistics.

An event log answers "what happened"; ANALYZE needs "what drives the outcome".
This deterministic transform rolls each case up to one row:

    case_id | cycle_hours | n_events | n_revisits | reworked |
    hours_in_<activity>... | <first value of every attribute column>...

so the Statistical Engine can run hypothesis tests / regression of
`cycle_hours` (or dwell times) against categorical attributes like team,
component, or priority. Zero LLM tokens.
"""

from __future__ import annotations

import re

import pandas as pd

_STANDARD = {"case_id", "activity", "timestamp"}


def _slug(activity: str) -> str:
    return re.sub(r"[^0-9a-zA-Z]+", "_", activity.strip()).strip("_").lower()


def case_feature_table(
    events: pd.DataFrame,
    attribute_columns: list[str] | None = None,
    max_dwell_activities: int = 20,
) -> pd.DataFrame:
    df = events.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="mixed")
    df = df.sort_values(["case_id", "timestamp"])

    if attribute_columns is None:
        attribute_columns = [c for c in df.columns if c not in _STANDARD]

    # Dwell time: hours from entering an activity until the next event.
    df["next_ts"] = df.groupby("case_id")["timestamp"].shift(-1)
    df["dwell_hours"] = (df["next_ts"] - df["timestamp"]).dt.total_seconds() / 3600

    top_activities = df["activity"].value_counts().head(max_dwell_activities).index
    dwell = (
        df[df["activity"].isin(top_activities)]
        .pivot_table(index="case_id", columns="activity", values="dwell_hours", aggfunc="sum")
        .rename(columns=lambda a: f"hours_in_{_slug(a)}")
        .fillna(0.0)
    )

    grouped = df.groupby("case_id")
    features = pd.DataFrame({
        "cycle_hours": (grouped["timestamp"].max() - grouped["timestamp"].min())
        .dt.total_seconds() / 3600,
        "n_events": grouped.size(),
        # revisits: events beyond the first visit to each activity = rework signal
        "n_revisits": grouped["activity"].agg(lambda s: len(s) - s.nunique()),
    })
    features["reworked"] = features["n_revisits"] > 0

    for col in attribute_columns:
        features[col] = grouped[col].first()

    return features.join(dwell).reset_index()
