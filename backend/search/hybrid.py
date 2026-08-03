"""Reciprocal Rank Fusion (RRF) — combines two ranked lists without needing
their scores to be on comparable scales (cosine similarity vs. our ad-hoc
keyword score aren't directly comparable, but rank position is)."""

from __future__ import annotations

_RRF_K = 60  # standard smoothing constant from the RRF literature


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
) -> dict[str, float]:
    """Given several ranked lists of the same kind of id, return fused scores.

    Higher fused score = more relevant. Ids absent from a list simply don't
    contribute a term for that list.
    """
    fused: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked):
            fused[item_id] = fused.get(item_id, 0.0) + 1.0 / (_RRF_K + rank + 1)
    return fused
