"""High-fidelity deterministic threat hunting simulator for offline and demo execution.

Generates realistic Gemini 3.7 Flash reasoning thoughts, tactical SQL queries,
and MITRE ATT&CK forensic correlations for offline benchmarking and instant UI testing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
try:
    from ..core.models import AgentDetection, HuntStep, MitreTactic, ScenarioTask
except (ImportError, ValueError):
    from core.models import AgentDetection, HuntStep, MitreTactic, ScenarioTask


class MockCyberHuntingEngine:
    """Simulates Gemini 3.7 Flash threat hunting responses across different agent harnesses."""

    @staticmethod
    def generate_antigravity_hunt_steps(scenario: ScenarioTask, thinking_budget: int = 2048) -> List[Dict[str, Any]]:
        """Simulate hierarchical Google Antigravity multi-agent investigation."""
        steps: List[Dict[str, Any]] = []
        gt_list = scenario.ground_truth_detections

        # Determine how many detections Antigravity finds based on thinking budget
        # Budget 2048+ finds 100% of ground truth (passes Simbian benchmark)
        # Budget 1024 finds 80%
        # Budget 0 finds 50%
        if thinking_budget >= 2048:
            selected_gt = gt_list
        elif thinking_budget >= 1024:
            selected_gt = gt_list[:max(1, int(len(gt_list) * 0.8))]
        else:
            selected_gt = gt_list[:max(1, int(len(gt_list) * 0.5))]

        # Step 1: Lead Threat Hunter (Orchestration & Triage)
        steps.append({
            "agent_role": "Lead Threat Hunter (Antigravity Orchestrator)",
            "thought": (
                f"[GEMINI 3.7 FLASH THINKING - Multi-Agent Orchestrator - Budget: {thinking_budget} tokens]\n"
                f"1. Triaging initial alert: '{scenario.initial_alert}'.\n"
                f"2. Contextualizing threat family: '{scenario.attack_family}' (Difficulty: {scenario.difficulty}).\n"
                f"3. Formulating investigative attack hypothesis: Assess Initial Access vector -> Process Execution anomalies -> Persistence -> Credential dumping / Evasion.\n"
                f"4. Dispatching SQL Telemetry Specialist to execute baseline process creation queries on events table."
            ),
            "action_type": "sql_query",
            "sql_query": (
                "SELECT id, timestamp, host, user, process_name, command_line, parent_process "
                "FROM events "
                "WHERE command_line LIKE '%powershell%' OR command_line LIKE '%cmd.exe%' "
                "   OR command_line LIKE '%certutil%' OR command_line LIKE '%wmic%' "
                "   OR command_line LIKE '%rundll32%' OR command_line LIKE '%vssadmin%' "
                "ORDER BY timestamp ASC LIMIT 15;"
            ),
            "new_findings": [
                AgentDetection(
                    tactic=gt.tactic,
                    technique_id=gt.technique_id,
                    technique_name=gt.technique_name,
                    confidence=0.98,
                    evidence_event_ids=gt.matched_event_ids,
                    explanation=f"Initial triage correlation verified {gt.technique_name}: {gt.indicator_summary}",
                    query_used="SELECT ... FROM events WHERE command_line LIKE '%...%'",
                )
                for gt in selected_gt if gt.tactic in (MitreTactic.INITIAL_ACCESS, MitreTactic.EXECUTION)
            ],
        })

        # Step 2: SQL Telemetry Specialist (Evasion, Persistence, & Privilege Escalation)
        steps.append({
            "agent_role": "SQL Telemetry Analyst",
            "thought": (
                f"[GEMINI 3.7 FLASH THINKING - SQL Telemetry Analyst]\n"
                f"1. Telemetry query identified initial process execution tree.\n"
                f"2. Drilling down into registry persistence (Event 13), scheduled tasks (4698), service creations (7045), and UAC / EDR tampering.\n"
                f"3. Searching for Living-off-the-Land evasion patterns and shadow copy manipulation."
            ),
            "action_type": "sql_query",
            "sql_query": (
                "SELECT id, timestamp, user, registry_path, file_path, command_line "
                "FROM events "
                "WHERE event_id IN (11, 12, 13, 4698, 7045) "
                "   OR registry_path LIKE '%Run%' OR registry_path LIKE '%ms-settings%' "
                "   OR command_line LIKE '%Set-MpPreference%' OR command_line LIKE '%wevtutil%' "
                "ORDER BY timestamp ASC LIMIT 15;"
            ),
            "new_findings": [
                AgentDetection(
                    tactic=gt.tactic,
                    technique_id=gt.technique_id,
                    technique_name=gt.technique_name,
                    confidence=0.96,
                    evidence_event_ids=gt.matched_event_ids,
                    explanation=f"Persistence / Evasion forensic analysis identified {gt.technique_name}: {gt.indicator_summary}",
                    query_used="SELECT ... FROM events WHERE event_id IN (11, 12, 13, 4698, 7045)",
                )
                for gt in selected_gt if gt.tactic in (MitreTactic.PERSISTENCE, MitreTactic.PRIVILEGE_ESCALATION, MitreTactic.DEFENSE_EVASION)
            ],
        })

        # Step 3: MITRE ATT&CK & Lateral Movement Hunter
        steps.append({
            "agent_role": "MITRE ATT&CK & Network Hunter",
            "thought": (
                f"[GEMINI 3.7 FLASH THINKING - Network & Lateral Specialist]\n"
                f"1. Correlating credential dumping (LSASS / SAM / IAM keys) with outbound lateral movement.\n"
                f"2. Inspecting remote WMI calls, RPC/SMB admin shares, network connection beacons (Event ID 3), and discovery commands.\n"
                f"3. Querying active network sockets and destination IPs."
            ),
            "action_type": "sql_query",
            "sql_query": (
                "SELECT id, timestamp, host, user, process_name, ip_address, port, command_line "
                "FROM events "
                "WHERE event_id = 3 OR ip_address IS NOT NULL OR command_line LIKE '%wmic%' OR command_line LIKE '%net %' "
                "ORDER BY timestamp ASC LIMIT 20;"
            ),
            "new_findings": [
                AgentDetection(
                    tactic=gt.tactic,
                    technique_id=gt.technique_id,
                    technique_name=gt.technique_name,
                    confidence=0.95,
                    evidence_event_ids=gt.matched_event_ids,
                    explanation=f"Lateral Movement / Credential Hunter verified {gt.technique_name}: {gt.indicator_summary}",
                    query_used="SELECT ... FROM events WHERE event_id = 3 OR ip_address IS NOT NULL",
                )
                for gt in selected_gt if gt.tactic in (MitreTactic.CREDENTIAL_ACCESS, MitreTactic.DISCOVERY, MitreTactic.LATERAL_MOVEMENT, MitreTactic.COMMAND_AND_CONTROL)
            ],
        })

        # Step 4: Forensic Evidence Verifier & Final Synthesis
        steps.append({
            "agent_role": "Forensic Evidence Verifier",
            "thought": (
                f"[GEMINI 3.7 FLASH THINKING - Forensic Evidence Verifier]\n"
                f"1. Validating collected evidence event IDs across the complete MITRE ATT&CK intrusion kill-chain.\n"
                f"2. Checking for data staging, archiving (7z/zip), cloud bucket uploads, or ransomware impact/encryption.\n"
                f"3. Eliminating potential false positives by cross-referencing parent PID relationships.\n"
                f"4. Generating comprehensive incident response verdict."
            ),
            "action_type": "submit_findings",
            "sql_query": None,
            "new_findings": [
                AgentDetection(
                    tactic=gt.tactic,
                    technique_id=gt.technique_id,
                    technique_name=gt.technique_name,
                    confidence=0.94,
                    evidence_event_ids=gt.matched_event_ids,
                    explanation=f"Final forensic verification confirmed {gt.technique_name}: {gt.indicator_summary}",
                )
                for gt in selected_gt if gt.tactic in (MitreTactic.COLLECTION, MitreTactic.EXFILTRATION, MitreTactic.IMPACT)
            ],
        })

        return steps

    @staticmethod
    def generate_opencode_hunt_steps(scenario: ScenarioTask, thinking_budget: int = 2048) -> List[Dict[str, Any]]:
        """Simulate Open Code single-agent CLI tool iterative investigation."""
        steps: List[Dict[str, Any]] = []
        gt_list = scenario.ground_truth_detections

        # OpenCode as a single CLI agent achieves ~60-70% recall on obvious indicators
        half_gt = [gt for idx, gt in enumerate(gt_list) if idx % 2 == 0 or gt.tactic in (MitreTactic.EXECUTION, MitreTactic.DEFENSE_EVASION)]

        # Step 1: Open Code inspects schema & runs broad SQL filter
        steps.append({
            "agent_role": "Open Code CLI Agent",
            "thought": (
                f"[GEMINI 3.7 FLASH - Open Code Harness - Budget: {thinking_budget}]\n"
                f"Inspecting telemetry schema and executing SQL query for process creations matching alert keywords."
            ),
            "action_type": "sql_query",
            "sql_query": (
                "SELECT id, timestamp, process_name, command_line "
                "FROM events "
                "WHERE command_line LIKE '%powershell%' OR command_line LIKE '%cmd%' OR command_line LIKE '%certutil%' "
                "LIMIT 10;"
            ),
            "new_findings": [
                AgentDetection(
                    tactic=gt.tactic,
                    technique_id=gt.technique_id,
                    technique_name=gt.technique_name,
                    confidence=0.89,
                    evidence_event_ids=gt.matched_event_ids,
                    explanation=f"OpenCode detected {gt.technique_name} via SQL query output: {gt.indicator_summary}",
                    query_used="SELECT ... FROM events WHERE command_line LIKE '%...%'",
                )
                for gt in half_gt if gt.tactic in (MitreTactic.INITIAL_ACCESS, MitreTactic.EXECUTION, MitreTactic.DEFENSE_EVASION)
            ],
        })

        # Step 2: Open Code checks network connections & persistence
        steps.append({
            "agent_role": "Open Code CLI Agent",
            "thought": (
                f"[GEMINI 3.7 FLASH - Open Code Harness]\n"
                f"Writing follow-up query to check network connections and registry modifications."
            ),
            "action_type": "sql_query",
            "sql_query": (
                "SELECT id, timestamp, process_name, ip_address, port, registry_path "
                "FROM events "
                "WHERE ip_address IS NOT NULL OR registry_path IS NOT NULL "
                "LIMIT 10;"
            ),
            "new_findings": [
                AgentDetection(
                    tactic=gt.tactic,
                    technique_id=gt.technique_id,
                    technique_name=gt.technique_name,
                    confidence=0.86,
                    evidence_event_ids=gt.matched_event_ids,
                    explanation=f"OpenCode identified {gt.technique_name} in network/persistence logs.",
                    query_used="SELECT ... FROM events WHERE ip_address IS NOT NULL",
                )
                for gt in half_gt if gt.tactic in (MitreTactic.PERSISTENCE, MitreTactic.COMMAND_AND_CONTROL, MitreTactic.IMPACT)
            ],
        })

        # Step 3: Open Code final wrap-up
        steps.append({
            "agent_role": "Open Code CLI Agent",
            "thought": (
                f"[GEMINI 3.7 FLASH - Open Code Harness]\n"
                f"Compiling final findings summary."
            ),
            "action_type": "submit_findings",
            "sql_query": None,
            "new_findings": [],
        })

        return steps
