"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    outcomes = {
        (POS, POS): "tp",
        ("PASS", POS): "fp",
        (POS, "PASS"): "fn",
        ("PASS", "PASS"): "tn",
    }
    for human_label, judge_label in zip(human, judge, strict=True):
        outcome = outcomes.get((human_label, judge_label))
        if outcome is None:
            raise ValueError("human and judge labels must be PASS or FAIL")
        counts[outcome] += 1
    return counts


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    counts = confusion(human, judge)
    true_positives = counts["tp"]
    predicted_positives = true_positives + counts["fp"]
    actual_positives = true_positives + counts["fn"]
    precision = true_positives / predicted_positives if predicted_positives else 0.0
    recall = true_positives / actual_positives if actual_positives else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    counts = confusion(human, judge)
    tp, fp, fn, tn = (counts[key] for key in ("tp", "fp", "fn", "tn"))
    total = tp + fp + fn + tn
    # Scale both agreement rates by total squared to keep the calculation exact until division.
    observed = (tp + tn) * total
    expected = (tp + fn) * (tp + fp) + (tn + fp) * (tn + fn)
    denominator = total**2 - expected
    if denominator == 0:
        raise ValueError("Cohen's kappa is undefined for empty data or perfect chance agreement")
    return (observed - expected) / denominator


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    denominator = sensitivity + specificity - 1.0
    if denominator == 0.0:
        raise ValueError("Rogan–Gladen correction is undefined when sensitivity and specificity sum to 1")
    corrected = (observed_rate + specificity - 1.0) / denominator
    return max(0.0, min(1.0, corrected))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap

    first = np.asarray(a, dtype=float)
    second = np.asarray(b, dtype=float)
    if first.ndim != 1 or first.shape != second.shape or first.size == 0:
        raise ValueError("paired bootstrap requires two non-empty, equally sized 1D samples")
    if not (np.isfinite(first).all() and np.isfinite(second).all()):
        raise ValueError("paired bootstrap samples must contain only finite values")
    if n_resamples < 1 or not 0 < confidence < 1:
        raise ValueError("paired bootstrap requires positive resamples and confidence between 0 and 1")

    def mean_difference(x, y, axis):
        return np.mean(x - y, axis=axis)

    delta = float(mean_difference(first, second, axis=0))
    if np.array_equal(first, second) or first.size == 1:
        return delta, delta, delta

    interval = bootstrap(
        (first, second),
        mean_difference,
        paired=True,
        method="percentile",
        confidence_level=confidence,
        n_resamples=n_resamples,
        rng=np.random.default_rng(rng),
    ).confidence_interval
    return delta, float(interval.low), float(interval.high)


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    # TODO M6
    raise NotImplementedError


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    # TODO M6
    raise NotImplementedError
