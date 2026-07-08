"""Pareto (80/20) analysis over defect/delay categories."""

from __future__ import annotations


def pareto_analysis(
    counts: dict[str, float], threshold: float = 0.80
) -> dict[str, object]:
    """Rank categories by contribution and find the 'vital few'.

    Returns categories sorted descending with cumulative share, plus the
    minimal set of categories covering `threshold` of the total.
    """
    if not counts:
        raise ValueError("pareto_analysis requires at least one category")
    if any(v < 0 for v in counts.values()):
        raise ValueError("counts must be non-negative")
    total = sum(counts.values())
    if total == 0:
        raise ValueError("all counts are zero")

    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    cumulative = 0.0
    rows: list[dict[str, float | str]] = []
    vital_few: list[str] = []
    for name, value in ranked:
        share = value / total
        cumulative += share
        rows.append({
            "category": name,
            "count": value,
            "share": round(share, 6),
            "cumulative_share": round(min(cumulative, 1.0), 6),
        })
        if len(vital_few) == 0 or rows[-2]["cumulative_share"] < threshold:  # type: ignore[index]
            vital_few.append(name)

    return {"rows": rows, "vital_few": vital_few, "threshold": threshold, "total": total}
