"""Multidimensional Stratified Partitioner for BenchHub.

Preserves joint feature distributions across multi-label behavioral capability tags
and discrete difficulty levels, guaranteeing strict non-leakage isolation between
Optimization and Holdout sets.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import math
import random
from typing import Any, Dict, Iterator, List, Optional, Sequence, Set, Tuple, Union
from pydantic import BaseModel, Field

from .schema import ATIFTask, BehavioralTag, BenchmarkSuite, DifficultyLevel


class DivergenceReport(BaseModel):
    """Comprehensive report of distribution balance and isolation between partitions."""
    difficulty_jsd: float = Field(..., description="Jensen-Shannon divergence for difficulty strata")
    difficulty_chi2_stat: float = Field(..., description="Chi-Square test statistic for difficulty")
    difficulty_p_value: float = Field(..., description="p-value for difficulty distribution independence")
    tag_jsds: Dict[str, float] = Field(default_factory=dict, description="JSD per behavioral tag")
    tag_chi2_stats: Dict[str, float] = Field(default_factory=dict, description="Chi-Square stat per behavioral tag")
    tag_p_values: Dict[str, float] = Field(default_factory=dict, description="p-value per behavioral tag")
    max_jsd: float = Field(..., description="Maximum JSD across all marginal dimensions")
    min_p_value: float = Field(..., description="Minimum p-value across all marginal dimensions")
    is_balanced: bool = Field(..., description="True if all testable dimensions have p-value >= alpha")
    is_leak_free: bool = Field(..., description="True if optimization and holdout task IDs are strictly disjoint")

    @property
    def jsd(self) -> float:
        """Alias for max_jsd."""
        return self.max_jsd


class SplitResult(BaseModel):
    """Immutable result of stratified benchmark suite partitioning."""
    optimization_tasks: List[ATIFTask] = Field(..., description="Optimization / training set tasks")
    holdout_tasks: List[ATIFTask] = Field(..., description="Isolated holdout / validation set tasks")
    total_tasks: int = Field(..., description="Total tasks in original suite")
    optimization_ratio: float = Field(..., description="Observed optimization set proportion")
    holdout_ratio: float = Field(..., description="Observed holdout set proportion")
    divergence_report: DivergenceReport = Field(..., description="Statistical divergence verification metrics")

    @property
    def optimization_set(self) -> List[ATIFTask]:
        """Alias for optimization_tasks for test compatibility."""
        return self.optimization_tasks

    @property
    def holdout_set(self) -> List[ATIFTask]:
        """Alias for holdout_tasks for test compatibility."""
        return self.holdout_tasks

    @property
    def optimization_suite(self) -> BenchmarkSuite:
        """Helper to package optimization tasks as a BenchmarkSuite."""
        return BenchmarkSuite(
            name="optimization_set",
            version="split-v1",
            tasks=self.optimization_tasks,
        )

    @property
    def holdout_suite(self) -> BenchmarkSuite:
        """Helper to package holdout tasks as a BenchmarkSuite."""
        return BenchmarkSuite(
            name="holdout_set",
            version="split-v1",
            tasks=self.holdout_tasks,
        )

    def __iter__(self) -> Iterator[BenchmarkSuite]:
        """Support tuple unpacking: opt_suite, hold_suite = splitter.split(benchmark)."""
        yield self.optimization_suite
        yield self.holdout_suite

    def __getitem__(self, idx: int) -> BenchmarkSuite:
        return [self.optimization_suite, self.holdout_suite][idx]


def jensen_shannon_divergence(p: Sequence[float], q: Sequence[float]) -> float:
    """Computes Jensen-Shannon distance D_JS(P || Q) with base-2 logarithm."""
    if len(p) != len(q):
        raise ValueError("Distributions must have identical support length")
    total_p, total_q = sum(p), sum(q)
    if total_p == 0.0 or total_q == 0.0:
        return 0.0
    norm_p = [x / total_p for x in p]
    norm_q = [y / total_q for y in q]
    m = [0.5 * (px + qx) for px, qx in zip(norm_p, norm_q)]

    def _kl(a: Sequence[float], b: Sequence[float]) -> float:
        kl = 0.0
        for ai, bi in zip(a, b):
            if ai > 0.0 and bi > 0.0:
                kl += ai * math.log2(ai / bi)
        return kl

    js = 0.5 * _kl(norm_p, m) + 0.5 * _kl(norm_q, m)
    return float(max(0.0, js))


def regularized_gamma_q(a: float, x: float) -> float:
    """Regularized upper incomplete gamma function Q(a, x) for Chi-Square survival."""
    if x <= 0.0 or a <= 0.0:
        return 1.0
    if abs(a - 0.5) < 1e-9:
        return float(math.erfc(math.sqrt(x)))

    sum_term = 1.0 / a
    current = sum_term
    for n in range(1, 200):
        current *= x / (a + n)
        sum_term += current
        if abs(current) < 1e-14 * abs(sum_term):
            break
    log_prefix = a * math.log(x) - x - math.lgamma(a)
    p = math.exp(log_prefix) * sum_term
    return float(max(0.0, min(1.0, 1.0 - p)))


def chi_square_contingency(observed: Sequence[Sequence[int]]) -> Tuple[float, float, int]:
    """Computes Pearson Chi-Square test statistic, p-value, and degrees of freedom for 2xK table."""
    r0, r1 = list(observed[0]), list(observed[1])
    row_totals = [sum(r0), sum(r1)]
    if row_totals[0] == 0 or row_totals[1] == 0:
        return 0.0, 0.0, 0

    try:
        import scipy.stats as stats  # type: ignore
        res = stats.chi2_contingency(observed, correction=False)
        return float(res.statistic), float(res.pvalue), int(res.dof)
    except (ImportError, Exception):
        pass

    k = len(r0)
    col_totals = [r0[j] + r1[j] for j in range(k)]
    total = sum(col_totals)
    valid_cols = [j for j in range(k) if col_totals[j] > 0]
    df = len(valid_cols) - 1
    if df <= 0 or total == 0:
        return 0.0, 0.0, 0

    stat = 0.0
    for i, row in enumerate([r0, r1]):
        for j in valid_cols:
            exp = (row_totals[i] * col_totals[j]) / total
            if exp > 0:
                stat += ((row[j] - exp) ** 2) / exp

    p_val = regularized_gamma_q(df / 2.0, stat / 2.0)
    return float(stat), float(p_val), int(df)


class StratifiedSplitter:
    """Multidimensional Stratified Partitioner preserving joint distributions across tags and difficulty."""

    def __init__(
        self,
        holdout_ratio: float = 0.30,
        opt_ratio: Optional[float] = None,
        split_ratio: Optional[float] = None,
        seed: Optional[int] = 42,
        random_seed: Optional[int] = None,
        alpha: float = 0.05,
    ):
        if split_ratio is not None and opt_ratio is None:
            if not (0.0 <= split_ratio <= 1.0) or math.isnan(split_ratio) or math.isinf(split_ratio):
                raise ValueError(f"Holdout ratio must be in (0, 1), got {1.0 - split_ratio}")
            holdout_ratio = 1.0 - split_ratio
        elif opt_ratio is not None:
            if not (0.0 < opt_ratio < 1.0) or math.isnan(opt_ratio) or math.isinf(opt_ratio):
                raise ValueError(f"Holdout ratio must be in (0, 1), got {1.0 - opt_ratio}")
            holdout_ratio = 1.0 - opt_ratio
        else:
            if not (0.0 < holdout_ratio < 1.0) or math.isnan(holdout_ratio) or math.isinf(holdout_ratio):
                raise ValueError(f"Holdout ratio must be in (0, 1), got {holdout_ratio}")

        effective_seed = random_seed if random_seed is not None else seed
        self.holdout_ratio = holdout_ratio
        self.opt_ratio = 1.0 - holdout_ratio
        self.seed = effective_seed
        self.random_seed = effective_seed
        self.alpha = alpha

    def split(
        self,
        benchmark: Union[BenchmarkSuite, Sequence[ATIFTask]],
        opt_ratio: Optional[float] = None,
        holdout_ratio: Optional[float] = None,
        split_ratio: Optional[float] = None,
    ) -> SplitResult:
        """Partitions benchmark suite into Optimization and Holdout sets with zero leakage."""
        tasks: List[ATIFTask] = benchmark.tasks if isinstance(benchmark, BenchmarkSuite) else list(benchmark)
        N = len(tasks)
        if N < 2:
            raise ValueError(f"Insufficient tasks: cannot perform stratified split on suite with {N} tasks (too few tasks, at least 2 tasks required)")

        # Upfront duplicate task_id validation
        seen_ids: Set[str] = set()
        for t in tasks:
            if t.task_id in seen_ids:
                raise ValueError(f"Duplicate task_id '{t.task_id}' detected in input sequence")
            seen_ids.add(t.task_id)

        # Resolve effective holdout ratio
        if split_ratio is not None:
            if not (0.0 <= split_ratio <= 1.0) or math.isnan(split_ratio) or math.isinf(split_ratio):
                raise ValueError(f"Holdout ratio must be in (0, 1), got {1.0 - split_ratio}")
            effective_holdout = 1.0 - split_ratio
        elif holdout_ratio is not None:
            if not (0.0 < holdout_ratio < 1.0) or math.isnan(holdout_ratio) or math.isinf(holdout_ratio):
                raise ValueError(f"Holdout ratio must be in (0, 1), got {holdout_ratio}")
            effective_holdout = holdout_ratio
        elif opt_ratio is not None:
            if not (0.0 < opt_ratio < 1.0) or math.isnan(opt_ratio) or math.isinf(opt_ratio):
                raise ValueError(f"Holdout ratio must be in (0, 1), got {1.0 - opt_ratio}")
            effective_holdout = 1.0 - opt_ratio
        else:
            effective_holdout = self.holdout_ratio

        if effective_holdout == 0.0:
            opt_tasks = list(tasks)
            hold_tasks = []
            report = self.compute_divergence(tasks, opt_tasks, hold_tasks)
            return SplitResult(
                optimization_tasks=opt_tasks,
                holdout_tasks=hold_tasks,
                total_tasks=N,
                optimization_ratio=1.0,
                holdout_ratio=0.0,
                divergence_report=report,
            )

        if effective_holdout == 1.0:
            opt_tasks = []
            hold_tasks = list(tasks)
            report = self.compute_divergence(tasks, opt_tasks, hold_tasks)
            return SplitResult(
                optimization_tasks=opt_tasks,
                holdout_tasks=hold_tasks,
                total_tasks=N,
                optimization_ratio=0.0,
                holdout_ratio=1.0,
                divergence_report=report,
            )

        rng = random.Random(self.seed)
        target_holdout = max(1, min(N - 1, round(N * effective_holdout)))
        target_opt = N - target_holdout

        # 1. Group tasks by composite stratum key
        strata: Dict[str, List[ATIFTask]] = defaultdict(list)
        for task in tasks:
            strata[task.composite_stratum_key].append(task)

        dense_keys = [k for k in sorted(strata.keys()) if len(strata[k]) > 1]
        singletons = [strata[k][0] for k in sorted(strata.keys()) if len(strata[k]) == 1]

        opt_tasks: List[ATIFTask] = []
        hold_tasks: List[ATIFTask] = []

        # 2. Dense Strata Splitting via Quota-Aware Pure Hamilton Apportionment
        if dense_keys:
            n_dense = sum(len(strata[k]) for k in dense_keys)
            n_singletons = len(singletons)

            min_dense_hold = max(0, target_holdout - n_singletons)
            max_dense_hold = min(target_holdout, n_dense)
            ideal_dense_hold = round(n_dense * effective_holdout)
            target_dense_hold = max(min_dense_hold, min(max_dense_hold, ideal_dense_hold))

            base_alloc: Dict[str, int] = {}
            remainders: List[Tuple[float, str]] = []
            for k in dense_keys:
                m = len(strata[k])
                ideal_h = m * (target_dense_hold / n_dense) if n_dense > 0 else 0.0
                base_h = int(math.floor(ideal_h))
                base_alloc[k] = base_h
                remainders.append((ideal_h - base_h, k))

            cur_dense_hold = sum(base_alloc.values())
            shortfall = target_dense_hold - cur_dense_hold
            remainders.sort(key=lambda x: (x[0], x[1]), reverse=True)
            for i in range(shortfall):
                k = remainders[i % len(remainders)][1]
                base_alloc[k] += 1

            for k in dense_keys:
                group = list(strata[k])
                group.sort(key=lambda x: x.task_id)
                rng.shuffle(group)
                h_count = base_alloc[k]
                opt_count = len(group) - h_count
                opt_tasks.extend(group[:opt_count])
                hold_tasks.extend(group[opt_count:])

        # 3. Singleton Strata Splitting via Greedy Divergence Minimization
        if singletons:
            singletons.sort(key=lambda x: x.task_id)
            rng.shuffle(singletons)

            all_diffs = sorted(list({t.difficulty.value for t in tasks}))
            all_tags = sorted(list({tag.value for t in tasks for tag in t.behavioral_tags}))

            target_prop_diff = {d: sum(1 for t in tasks if t.difficulty.value == d) / N for d in all_diffs}
            target_prop_tags = {b: sum(1 for t in tasks if any(bt.value == b for bt in t.behavioral_tags)) / N for b in all_tags}

            diff_count_opt = Counter(t.difficulty.value for t in opt_tasks)
            diff_count_hold = Counter(t.difficulty.value for t in hold_tasks)
            tag_count_opt = Counter(b.value for t in opt_tasks for b in t.behavioral_tags)
            tag_count_hold = Counter(b.value for t in hold_tasks for b in t.behavioral_tags)

            for t in singletons:
                rem_opt = target_opt - len(opt_tasks)
                rem_hold = target_holdout - len(hold_tasks)
                t_diff = t.difficulty.value
                t_tag_vals = [tag.value for tag in t.behavioral_tags]

                if rem_opt <= 0:
                    hold_tasks.append(t)
                    diff_count_hold[t_diff] += 1
                    for b in t_tag_vals:
                        tag_count_hold[b] += 1
                    continue
                if rem_hold <= 0:
                    opt_tasks.append(t)
                    diff_count_opt[t_diff] += 1
                    for b in t_tag_vals:
                        tag_count_opt[b] += 1
                    continue

                def _score_placement(is_opt: bool) -> float:
                    curr_len = len(opt_tasks) if is_opt else len(hold_tasks)
                    new_len = curr_len + 1
                    curr_diff = diff_count_opt if is_opt else diff_count_hold
                    curr_tags = tag_count_opt if is_opt else tag_count_hold
                    err = 0.0
                    for d in all_diffs:
                        c = curr_diff[d] + (1 if t_diff == d else 0)
                        err += (c / new_len - target_prop_diff[d]) ** 2
                    for b in all_tags:
                        c = curr_tags[b] + (1 if b in t_tag_vals else 0)
                        err += (c / new_len - target_prop_tags[b]) ** 2
                    return err

                if _score_placement(True) <= _score_placement(False):
                    opt_tasks.append(t)
                    diff_count_opt[t_diff] += 1
                    for b in t_tag_vals:
                        tag_count_opt[b] += 1
                else:
                    hold_tasks.append(t)
                    diff_count_hold[t_diff] += 1
                    for b in t_tag_vals:
                        tag_count_hold[b] += 1

        # 4. Verification & Reporting
        if len(opt_tasks) == 0 or len(hold_tasks) == 0:
            raise ValueError(
                f"Partitioning invariant violated: both partitions must be non-empty "
                f"(optimization: {len(opt_tasks)}, holdout: {len(hold_tasks)})"
            )

        report = self.compute_divergence(tasks, opt_tasks, hold_tasks)
        return SplitResult(
            optimization_tasks=opt_tasks,
            holdout_tasks=hold_tasks,
            total_tasks=N,
            optimization_ratio=len(opt_tasks) / N,
            holdout_ratio=len(hold_tasks) / N,
            divergence_report=report,
        )

    def verify_non_leakage(self, opt_tasks: Sequence[ATIFTask], hold_tasks: Sequence[ATIFTask]) -> bool:
        """Verifies strict disjointness between optimization and holdout partitions."""
        opt_ids = {t.task_id for t in opt_tasks}
        hold_ids = {t.task_id for t in hold_tasks}
        return opt_ids.isdisjoint(hold_ids)

    def verify_divergence(
        self,
        opt_tasks: Sequence[ATIFTask],
        hold_tasks: Sequence[ATIFTask],
    ) -> DivergenceReport:
        """Convenience method to verify divergence between two sets of tasks."""
        all_tasks = list(opt_tasks) + list(hold_tasks)
        return self.compute_divergence(all_tasks, opt_tasks, hold_tasks)

    def compute_divergence(
        self,
        all_tasks: Sequence[ATIFTask],
        opt_tasks: Sequence[ATIFTask],
        hold_tasks: Sequence[ATIFTask],
    ) -> DivergenceReport:
        """Calculates JSD, Chi-Square statistics, p-values, and non-leakage verification."""
        is_leak_free = self.verify_non_leakage(opt_tasks, hold_tasks)
        all_diffs = sorted(list({t.difficulty.value for t in all_tasks}))
        all_tags = sorted(list({tag.value for t in all_tasks for tag in t.behavioral_tags}))

        # Guard against degenerate empty partitions
        if len(opt_tasks) == 0 or len(hold_tasks) == 0:
            return DivergenceReport(
                difficulty_jsd=1.0,
                difficulty_chi2_stat=0.0,
                difficulty_p_value=0.0,
                tag_jsds={b: 1.0 for b in all_tags},
                tag_chi2_stats={b: 0.0 for b in all_tags},
                tag_p_values={b: 0.0 for b in all_tags},
                max_jsd=1.0,
                min_p_value=0.0,
                is_balanced=False,
                is_leak_free=False,
            )

        opt_len = max(1, len(opt_tasks))
        hold_len = max(1, len(hold_tasks))

        # Difficulty JSD & Chi2
        p_diff = [sum(1 for t in opt_tasks if t.difficulty.value == d) / opt_len for d in all_diffs]
        q_diff = [sum(1 for t in hold_tasks if t.difficulty.value == d) / hold_len for d in all_diffs]
        diff_jsd = jensen_shannon_divergence(p_diff, q_diff)

        obs_diff = [
            [sum(1 for t in opt_tasks if t.difficulty.value == d) for d in all_diffs],
            [sum(1 for t in hold_tasks if t.difficulty.value == d) for d in all_diffs],
        ]
        diff_stat, diff_p_val, _ = chi_square_contingency(obs_diff)

        # Behavioral Tags JSD & Chi2
        tag_jsds: Dict[str, float] = {}
        tag_chi2_stats: Dict[str, float] = {}
        tag_p_values: Dict[str, float] = {}

        for b in all_tags:
            c_opt = sum(1 for t in opt_tasks if any(bt.value == b for bt in t.behavioral_tags))
            c_hold = sum(1 for t in hold_tasks if any(bt.value == b for bt in t.behavioral_tags))
            p_b = c_opt / opt_len
            q_b = c_hold / hold_len
            tag_jsds[b] = jensen_shannon_divergence([p_b, 1.0 - p_b], [q_b, 1.0 - q_b])

            table = [
                [c_opt, len(opt_tasks) - c_opt],
                [c_hold, len(hold_tasks) - c_hold],
            ]
            stat, p_val, _ = chi_square_contingency(table)
            tag_chi2_stats[b] = stat
            tag_p_values[b] = p_val

        all_jsds = [diff_jsd] + list(tag_jsds.values())
        all_p_values = [diff_p_val] + list(tag_p_values.values())
        max_jsd = max(all_jsds) if all_jsds else 0.0
        min_p_val = min(all_p_values) if all_p_values else 1.0
        is_balanced = (len(opt_tasks) > 0) and (len(hold_tasks) > 0) and (min_p_val >= self.alpha) and is_leak_free

        return DivergenceReport(
            difficulty_jsd=diff_jsd,
            difficulty_chi2_stat=diff_stat,
            difficulty_p_value=diff_p_val,
            tag_jsds=tag_jsds,
            tag_chi2_stats=tag_chi2_stats,
            tag_p_values=tag_p_values,
            max_jsd=max_jsd,
            min_p_value=min_p_val,
            is_balanced=is_balanced,
            is_leak_free=is_leak_free,
        )


# Backward compatibility aliases
StratifiedSplit = SplitResult
MultidimensionalStratifiedSplitter = StratifiedSplitter


def calculate_divergence(
    a: Union[Dict[str, float], Sequence[float]],
    b: Union[Dict[str, float], Sequence[float]],
) -> float:
    """Calculates Jensen-Shannon divergence between two distributions (supports dicts or sequences)."""
    if isinstance(a, dict) and isinstance(b, dict):
        all_keys = sorted(list(set(a.keys()) | set(b.keys())))
        p = [float(a.get(k, 0.0)) for k in all_keys]
        q = [float(b.get(k, 0.0)) for k in all_keys]
        return jensen_shannon_divergence(p, q)
    return jensen_shannon_divergence(a, b)  # type: ignore


def chi_square_divergence(
    observed: Sequence[Any],
    expected: Optional[Sequence[Any]] = None,
) -> Tuple[float, float, int]:
    """Computes Chi-Square divergence, accepting either a 2xK table or (observed, expected) pair."""
    if expected is not None:
        table = [list(observed), list(expected)]
    else:
        table = list(observed)
    return chi_square_contingency(table)


compute_distribution_divergence = calculate_divergence


def stratified_split(
    benchmark: Union[BenchmarkSuite, Sequence[ATIFTask]],
    split_ratio: float = 0.70,
    holdout_ratio: Optional[float] = None,
    seed: Optional[int] = 42,
) -> SplitResult:
    """Convenience function for stratified benchmark splitting."""
    splitter = StratifiedSplitter(
        opt_ratio=split_ratio if holdout_ratio is None else None,
        holdout_ratio=holdout_ratio if holdout_ratio is not None else (1.0 - split_ratio),
        seed=seed,
    )
    return splitter.split(benchmark)

