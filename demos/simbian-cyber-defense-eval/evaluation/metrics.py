"""Simbian Cyber Defense Benchmark Metric definitions and scoring algorithms.

Implements the official Simbian benchmark scoring criteria:
- Per-tactic Recall, Precision, F1
- Strict Simbian Passing Bar: >= 50% recall on EVERY MITRE ATT&CK tactic in the attack chain
- Query Efficiency: Detections per SQL query
- False Discovery Rate (FDR)
"""

from typing import Dict, List
try:
    from ..core.models import (
        AgentDetection,
        EvaluationMetricResult,
        GroundTruthDetection,
        MitreTactic,
        ScenarioTask,
        TacticScore,
    )
except (ImportError, ValueError):
    from core.models import (
        AgentDetection,
        EvaluationMetricResult,
        GroundTruthDetection,
        MitreTactic,
        ScenarioTask,
        TacticScore,
    )


def compute_simbian_metrics(
    scenario: ScenarioTask,
    agent_detections: List[AgentDetection],
    total_queries: int,
    agent_name: str,
    model_name: str,
    thinking_budget: int,
    pass_threshold: float = 0.50,
) -> EvaluationMetricResult:
    """Compute complete Simbian benchmark evaluation metrics."""
    ground_truth = scenario.ground_truth_detections

    gt_by_technique: Dict[str, GroundTruthDetection] = {
        gt.technique_id.upper(): gt for gt in ground_truth
    }
    gt_by_tactic: Dict[MitreTactic, List[GroundTruthDetection]] = {}
    for gt in ground_truth:
        gt_by_tactic.setdefault(gt.tactic, []).append(gt)

    # Classify detections as True Positive or False Positive
    for det in agent_detections:
        tech_id = det.technique_id.upper().strip()
        matched = gt_by_technique.get(tech_id)
        if not matched:
            parent_id = tech_id.split(".")[0]
            for g_id, g_obj in gt_by_technique.items():
                if g_id.startswith(parent_id) or parent_id == g_id:
                    matched = g_obj
                    break

        if matched:
            det.is_true_positive = True
            det.matched_ground_truth_rule = matched.rule_id
        else:
            det.is_true_positive = False

    # Aggregate by tactic
    all_tactics = set(scenario.tactics_present)
    for gt in ground_truth:
        all_tactics.add(gt.tactic)
    for det in agent_detections:
        all_tactics.add(det.tactic)

    tactic_scores: Dict[str, TacticScore] = {}
    total_tp = 0
    total_fp = 0
    total_fn = 0
    all_tactics_cleared = True

    for tactic in all_tactics:
        tactic_gt = gt_by_tactic.get(tactic, [])
        gt_count = len(tactic_gt)

        tp = sum(1 for d in agent_detections if d.tactic == tactic and d.is_true_positive)
        fp = sum(1 for d in agent_detections if d.tactic == tactic and not d.is_true_positive)
        fn = max(0, gt_count - tp)

        rec = (tp / gt_count) if gt_count > 0 else (1.0 if fp == 0 else 0.0)
        prec = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        passed = (rec >= pass_threshold) if gt_count > 0 else True
        if gt_count > 0 and not passed:
            all_tactics_cleared = False

        tactic_scores[tactic.value] = TacticScore(
            tactic=tactic,
            ground_truth_count=gt_count,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            recall=round(rec, 3),
            precision=round(prec, 3),
            f1_score=round(f1, 3),
            passed_simbian_bar=passed,
        )
        total_tp += tp
        total_fp += fp
        total_fn += fn

    total_gt = len(ground_truth)
    overall_rec = (total_tp / total_gt) if total_gt > 0 else 0.0
    overall_prec = (total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else 0.0
    overall_f1 = (2 * overall_prec * overall_rec / (overall_prec + overall_rec)) if (overall_prec + overall_rec) > 0 else 0.0

    present_t_with_tp = sum(
        1 for t in scenario.tactics_present if tactic_scores.get(t.value, TacticScore(tactic=t)).true_positives > 0
    )
    chain_coverage = (present_t_with_tp / len(scenario.tactics_present)) if scenario.tactics_present else 0.0

    query_efficiency = round(total_tp / max(1, total_queries), 3)
    fdr = round(total_fp / max(1, total_tp + total_fp), 3)
    simbian_pass = all_tactics_cleared and (len(scenario.tactics_present) > 0)

    verdict = (
        "PASSED SIMBIAN BENCHMARK (Recall >= 50% across all tactics)"
        if simbian_pass
        else "FAILED SIMBIAN BENCHMARK (Incomplete attack coverage)"
    )

    return EvaluationMetricResult(
        scenario_id=scenario.id,
        agent_name=agent_name,
        model_name=model_name,
        thinking_budget=thinking_budget,
        tactic_scores=tactic_scores,
        overall_recall=round(overall_rec, 3),
        overall_precision=round(overall_prec, 3),
        overall_f1=round(overall_f1, 3),
        mitre_chain_coverage=round(chain_coverage, 3),
        query_efficiency_score=query_efficiency,
        false_discovery_rate=fdr,
        simbian_pass_status=simbian_pass,
        summary_verdict=verdict,
    )
