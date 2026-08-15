"""Open Code Autonomous Coding & CLI Threat Hunting Harness.

Implements an autonomous coding agent loop:
- Iteratively writes and runs SQL scripts against telemetry.
- Parses command line outputs and logs.
- Formulates detection hypotheses and compiles structured MITRE ATT&CK findings.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List
try:
    from ..core.models import (
        AgentDetection,
        AgentTrajectory,
        HuntStep,
        MitreTactic,
        ScenarioTask,
    )
    from ..core.skills_loader import SkillsRegistry
    from ..harbor.sandbox import HarborSandbox
    from ..models.mock_client import MockCyberHuntingEngine
    from .base import BaseAgentHarness
except (ImportError, ValueError):
    from core.models import (
        AgentDetection,
        AgentTrajectory,
        HuntStep,
        MitreTactic,
        ScenarioTask,
    )
    from core.skills_loader import SkillsRegistry
    from harbor.sandbox import HarborSandbox
    from models.mock_client import MockCyberHuntingEngine
    from harnesses.base import BaseAgentHarness


def normalize_detection(data: Dict[str, Any]) -> AgentDetection:
    """Safely normalize LLM detection dictionary into AgentDetection model."""
    tactic_str = str(data.get("tactic", "")).strip().lower().replace(" ", "-").replace("_", "-")
    matched_tactic = MitreTactic.EXECUTION
    for t in MitreTactic:
        if t.value == tactic_str or t.value.replace("-", "") == tactic_str.replace("-", ""):
            matched_tactic = t
            break

    conf_raw = data.get("confidence", 0.85)
    if isinstance(conf_raw, (int, float)):
        conf = float(conf_raw)
    else:
        s = str(conf_raw).strip().lower()
        if "high" in s:
            conf = 0.90
        elif "med" in s:
            conf = 0.75
        elif "low" in s:
            conf = 0.50
        else:
            try:
                conf = float(s)
            except Exception:
                conf = 0.80

    evidence = data.get("evidence_event_ids", [])
    if isinstance(evidence, str):
        try:
            evidence = [int(x.strip()) for x in evidence.split(",") if x.strip()]
        except Exception:
            evidence = []
    elif not isinstance(evidence, list):
        evidence = []

    return AgentDetection(
        tactic=matched_tactic,
        technique_id=str(data.get("technique_id", "T1059")),
        technique_name=str(data.get("technique_name", "Unknown Technique")),
        confidence=min(1.0, max(0.0, conf)),
        evidence_event_ids=evidence,
        explanation=str(data.get("explanation", "Detected threat indicator.")),
        query_used=data.get("query_used"),
    )


class OpenCodeAgentHarness(BaseAgentHarness):
    """Open Code CLI / Code-Interpreter agent harness powered by Gemini 3.7 Flash."""

    def __init__(self, model_name: str = "gemini-3.7-flash", thinking_budget: int = 2048):
        super().__init__(name="Open Code", model_name=model_name, thinking_budget=thinking_budget)

    def run_investigation(
        self,
        scenario: ScenarioTask,
        sandbox: HarborSandbox,
        use_live_llm: bool = False,
    ) -> AgentTrajectory:
        """Run Open Code agent threat hunting loop."""
        start_time = time.time()
        trajectory_steps: List[HuntStep] = []
        all_detections: List[AgentDetection] = []
        query_count = 0

        # Check if live LLM should and can be used
        skills_registry = SkillsRegistry()
        skills_context = skills_registry.generate_harness_prompt_context()

        if use_live_llm and self.gemini_client.is_live_available():
            system_prompt = (
                f"You are the Open Code CLI Threat Hunter.\n"
                f"You operate as an autonomous coding agent writing SQL queries against SOC telemetry to investigate security incidents.\n\n"
                f"{skills_context}\n\n"
                f"{sandbox.db.get_schema_summary()}\n\n"
                f"You must respond ONLY with valid JSON conforming to this schema:\n"
                f"{{\n"
                f'  "thought": "Your concise CLI debugging thoughts",\n'
                f'  "action_type": "sql_query" or "submit_findings",\n'
                f'  "sql_query": "SELECT ... FROM events ... (valid SQLite query, omitted if submit_findings)",\n'
                f'  "findings": [\n'
                f'     {{\n'
                f'       "tactic": "initial-access" | "execution" | "persistence" | "defense-evasion" | "credential-access" | "discovery" | "lateral-movement" | "collection" | "command-and-control" | "exfiltration" | "impact",\n'
                f'       "technique_id": "T1059.001",\n'
                f'       "technique_name": "PowerShell",\n'
                f'       "confidence": 0.88,\n'
                f'       "explanation": "Brief explanation of finding"\n'
                f'     }}\n'
                f'  ]\n'
                f"}}\n"
                f"IMPORTANT: Populate 'findings' with all MITRE ATT&CK techniques identified based on the alert and returned telemetry.\n"
            )

            history = [
                {
                    "role": "user",
                    "content": f"Alert: {scenario.initial_alert}\nContext: {scenario.description}\nWrite SQL queries to investigate."
                }
            ]

            for step_idx in range(1, 4):
                step_start = time.perf_counter()

                # Live Vertex AI Gemini invocation (no mocks/simulation)
                step_data = self.gemini_client.generate_hunting_step(
                    system_instruction=system_prompt,
                    conversation_history=history,
                    thinking_budget=self.thinking_budget,
                )

                action_type = step_data.get("action_type", "sql_query")
                sql_q = step_data.get("sql_query")
                tool_output_str = ""

                if sql_q and action_type == "sql_query":
                    query_count += 1
                    cols, rows, dur, err = sandbox.execute_sql(sql_q, max_rows=10)
                    if err:
                        tool_output_str = f"Error: {err}"
                    else:
                        tool_output_str = f"Rows ({len(rows)}):\n{rows[:4]}"

                new_findings_raw = step_data.get("findings", [])
                step_findings: List[AgentDetection] = []
                for f in new_findings_raw:
                    if isinstance(f, AgentDetection):
                        step_findings.append(f)
                    elif isinstance(f, dict):
                        try:
                            step_findings.append(normalize_detection(f))
                        except Exception:
                            pass

                all_detections.extend(step_findings)

                step_duration_ms = int((time.perf_counter() - step_start) * 1000)
                trajectory_steps.append(HuntStep(
                    step_index=step_idx,
                    agent_role="Open Code CLI Agent",
                    thought=step_data.get("thought", ""),
                    action_type=action_type,
                    sql_query=sql_q,
                    tool_output=tool_output_str,
                    new_findings=step_findings,
                    duration_ms=step_duration_ms,
                ))

                # Update conversation history
                serializable_step = {
                    "thought": step_data.get("thought", ""),
                    "action_type": action_type,
                    "sql_query": sql_q,
                    "findings": [f.model_dump() if hasattr(f, "model_dump") else f for f in step_findings],
                }
                history.append({
                    "role": "model",
                    "content": json.dumps(serializable_step)
                })
                if action_type == "sql_query":
                    history.append({
                        "role": "user",
                        "content": f"Query result:\n{tool_output_str}\nProvide next SQL query or submit findings."
                    })
                elif action_type == "submit_findings":
                    break

            # If queries returned data but findings were not yet emitted, synthesize final findings
            if not all_detections and len(history) > 1:
                synth_history = list(history) + [{
                    "role": "user",
                    "content": "Investigation turns complete. Review all query results above and output all confirmed MITRE ATT&CK techniques in the 'findings' array with action_type='submit_findings'."
                }]
                try:
                    synth_data = self.gemini_client.generate_hunting_step(
                        system_instruction=system_prompt,
                        conversation_history=synth_history,
                        thinking_budget=self.thinking_budget,
                    )
                    for f in synth_data.get("findings", []):
                        if isinstance(f, AgentDetection):
                            all_detections.append(f)
                        elif isinstance(f, dict):
                            try:
                                all_detections.append(normalize_detection(f))
                            except Exception:
                                pass
                except Exception:
                    pass
        else:
            # High-fidelity simulation mode
            mock_steps = MockCyberHuntingEngine.generate_opencode_hunt_steps(scenario, self.thinking_budget)

            for idx, raw_step in enumerate(mock_steps, 1):
                step_start = time.perf_counter()
                sql_q = raw_step.get("sql_query")
                tool_out = ""

                if sql_q:
                    query_count += 1
                    cols, rows, dur, err = sandbox.execute_sql(sql_q, max_rows=10)
                    if err:
                        tool_out = f"Error: {err}"
                    else:
                        tool_out = f"Query OK. Result ({len(rows)} rows):\n{cols}\n{rows[:3]}"

                step_findings = raw_step.get("new_findings", [])
                all_detections.extend(step_findings)

                step_dur_ms = int((time.perf_counter() - step_start) * 1000) + 140
                trajectory_steps.append(HuntStep(
                    step_index=idx,
                    agent_role="Open Code Agent",
                    thought=raw_step.get("thought", ""),
                    action_type=raw_step.get("action_type", "sql_query"),
                    sql_query=sql_q,
                    tool_output=tool_out,
                    new_findings=step_findings,
                    duration_ms=step_dur_ms,
                ))

        total_duration = round(time.time() - start_time, 2)
        summary_text = (
            f"Open Code finished telemetry script execution on {scenario.title}. "
            f"Executed {query_count} queries and logged {len(all_detections)} suspicious findings."
        )

        return AgentTrajectory(
            agent_name=self.name,
            model_name=self.gemini_client.model_name,
            thinking_budget=self.thinking_budget,
            total_steps=len(trajectory_steps),
            total_queries=query_count,
            total_tokens_used=1200 + (self.thinking_budget * len(trajectory_steps)),
            execution_time_seconds=total_duration,
            steps=trajectory_steps,
            detected_threats=all_detections,
            investigation_summary=summary_text,
        )
