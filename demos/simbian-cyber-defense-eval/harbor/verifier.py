"""Harbor Ground-Truth Verifier for Simbian Cyber Defense Benchmark.

Scores agent detections against scenario ground-truth Sigma rules and attack procedures.
Calculates per-tactic and overall Recall, Precision, F1, and Simbian passing status.
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple
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


class HarborVerifier:
    """Verifies and grades agent threat hunting detections against ground truth."""

    def __init__(self, simbian_pass_threshold: float = 0.50):
        self.simbian_pass_threshold = simbian_pass_threshold

    def verify_detections(
        self,
        scenario: ScenarioTask,
        agent_detections: List[AgentDetection],
        total_queries: int = 1,
        agent_name: str = "Unknown Agent",
        model_name: str = "gemini-3.7-flash",
        thinking_budget: int = 2048,
    ) -> EvaluationMetricResult:
        """Score agent detections against scenario ground truth and compute Simbian benchmark metrics.

        Args:
            scenario (ScenarioTask): BenchHub scenario metadata and ground-truth Sigma detections.
            agent_detections (List[AgentDetection]): The detections submitted by the evaluated agent.
            total_queries (int, optional): Total count of investigative SQL queries executed. Defaults to 1.
            agent_name (str, optional): Identifier of the agent harness. Defaults to "Unknown Agent".
            model_name (str, optional): Model evaluated. Defaults to "gemini-3.7-flash".
            thinking_budget (int, optional): Reasoning budget used. Defaults to 2048.

        Returns:
            EvaluationMetricResult: Comprehensive scorecard containing overall recall, precision, F1, FDR,
                per-tactic recall breakdowns, and Simbian pass/fail determination.
        """
        ground_truth = scenario.ground_truth_detections

        # Map ground truth by technique_id and tactic
        gt_by_technique: Dict[str, GroundTruthDetection] = {
            gt.technique_id.upper(): gt for gt in ground_truth
        }
        gt_by_tactic: Dict[MitreTactic, List[GroundTruthDetection]] = {}
        for gt in ground_truth:
            gt_by_tactic.setdefault(gt.tactic, []).append(gt)

        # Track matched ground truths
        matched_gt_rules: Set[str] = set()

        # Grade each agent detection
        graded_detections: List[AgentDetection] = []
        for det in agent_detections:
            tech_id = det.technique_id.upper().strip()
            # Technique match or sub-technique parent match
            matched_gt: GroundTruthDetection | None = None
            if tech_id in gt_by_technique:
                matched_gt = gt_by_technique[tech_id]
            else:
                # Try parent technique match (e.g. T1059 matches T1059.001)
                parent_id = tech_id.split(".")[0]
                for gt_id, gt_obj in gt_by_technique.items():
                    if gt_id.startswith(parent_id) or parent_id == gt_id:
                        matched_gt = gt_obj
                        break

            if matched_gt:
                det.is_true_positive = True
                det.matched_ground_truth_rule = matched_gt.rule_id
                matched_gt_rules.add(matched_gt.rule_id)
            else:
                det.is_true_positive = False
                det.matched_ground_truth_rule = None
            graded_detections.append(det)

        # Calculate per-tactic scores across all tactics present in scenario or detected
        all_tactics = set(scenario.tactics_present)
        for det in agent_detections:
            all_tactics.add(det.tactic)
        for gt in ground_truth:
            all_tactics.add(gt.tactic)

        tactic_scores: Dict[str, TacticScore] = {}
        total_tp = 0
        total_fp = 0
        total_fn = 0
        all_tactics_passed = True

        for tactic in all_tactics:
            tactic_gt = gt_by_tactic.get(tactic, [])
            gt_count = len(tactic_gt)

            # Count TPs for this tactic
            tp = sum(1 for det in graded_detections if det.tactic == tactic and det.is_true_positive)
            # Count FPs for this tactic
            fp = sum(1 for det in graded_detections if det.tactic == tactic and not det.is_true_positive)
            # Count FNs
            fn = max(0, gt_count - tp)

            recall = (tp / gt_count) if gt_count > 0 else (1.0 if fp == 0 else 0.0)
            precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

            # Check if this tactic meets the Simbian passing bar (>= 50% recall)
            passed_bar = (recall >= self.simbian_pass_threshold) if gt_count > 0 else True
            if gt_count > 0 and not passed_bar:
                all_tactics_passed = False

            tactic_scores[tactic.value] = TacticScore(
                tactic=tactic,
                ground_truth_count=gt_count,
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                recall=round(recall, 3),
                precision=round(precision, 3),
                f1_score=round(f1, 3),
                passed_simbian_bar=passed_bar,
            )

            total_tp += tp
            total_fp += fp
            total_fn += fn

        total_gt = len(ground_truth)
        overall_recall = (total_tp / total_gt) if total_gt > 0 else 0.0
        overall_precision = (total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else 0.0
        overall_f1 = (2 * overall_precision * overall_recall / (overall_precision + overall_recall)) if (overall_precision + overall_recall) > 0 else 0.0

        # Coverage of attack chain (% of scenario tactics with at least one TP)
        scenario_tactics_with_tp = sum(
            1 for t in scenario.tactics_present if tactic_scores.get(t.value, TacticScore(tactic=t)).true_positives > 0
        )
        mitre_chain_coverage = (scenario_tactics_with_tp / len(scenario.tactics_present)) if scenario.tactics_present else 0.0

        # Query Efficiency: True Positives per SQL Query
        query_efficiency = round(total_tp / max(1, total_queries), 3)

        # False Discovery Rate (FDR): FP / (TP + FP)
        fdr = round((total_fp / max(1, total_tp + total_fp)), 3)

        # Simbian benchmark strict pass condition: >= 50% recall on EVERY tactic
        simbian_pass = all_tactics_passed and (len(scenario.tactics_present) > 0)

        verdict = "PASSED SIMBIAN BENCHMARK (>=50% recall across all tactics)" if simbian_pass else "FAILED SIMBIAN BENCHMARK (Sub-50% recall on one or more tactics)"

        return EvaluationMetricResult(
            scenario_id=scenario.id,
            agent_name=agent_name,
            model_name=model_name,
            thinking_budget=thinking_budget,
            tactic_scores=tactic_scores,
            overall_recall=round(overall_recall, 3),
            overall_precision=round(overall_precision, 3),
            overall_f1=round(overall_f1, 3),
            mitre_chain_coverage=round(mitre_chain_coverage, 3),
            query_efficiency_score=query_efficiency,
            false_discovery_rate=fdr,
            simbian_pass_status=simbian_pass,
            summary_verdict=verdict,
        )
