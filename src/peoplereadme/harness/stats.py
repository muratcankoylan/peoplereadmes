"""Statistics for the harness: bootstrap CIs, Cohen's kappa, weighted accuracy."""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence


def weighted_mean(values: Sequence[float], weights: Sequence[float]) -> float:
    total = sum(weights)
    if total == 0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights, strict=True)) / total


def bootstrap_ci(
    values: Sequence[float],
    weights: Sequence[float],
    statistic: Callable[[Sequence[float], Sequence[float]], float],
    n_resamples: int = 1000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile bootstrap CI over (value, weight) pairs."""
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    stats = []
    for _ in range(n_resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        stats.append(statistic([values[i] for i in idx], [weights[i] for i in idx]))
    stats.sort()
    lo = stats[int((alpha / 2) * n_resamples)]
    hi = stats[min(int((1 - alpha / 2) * n_resamples), n_resamples - 1)]
    return (round(lo, 4), round(hi, 4))


def cohens_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    """Cohen's kappa for two raters over the same items (any label set)."""
    if len(a) != len(b) or not a:
        raise ValueError("raters must score the same non-empty items")
    n = len(a)
    labels = sorted(set(a) | set(b))
    observed = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    expected = sum(
        (sum(1 for x in a if x == lab) / n) * (sum(1 for y in b if y == lab) / n)
        for lab in labels
    )
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1 - expected)


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))
