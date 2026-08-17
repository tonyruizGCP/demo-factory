"""Core data models and schemas for the Cyber Defense Benchmark evaluation system.

Defines Pydantic models for MITRE ATT&CK structures, telemetry log events,
agent hunting steps, trajectories, benchmark tasks, and evaluation metrics.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MitreTactic(str, Enum):
    """The 12 Enterprise MITRE ATT&CK tactics evaluated in the Simbian benchmark."""
    INITIAL_ACCESS = "initial-access"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    PRIVILEGE_ESCALATION = "privilege-escalation"
    DEFENSE_EVASION = "defense-evasion"
    CREDENTIAL_ACCESS = "credential-access"
    DISCOVERY = "discovery"
    LATERAL_MOVEMENT = "lateral-movement"
    COLLECTION = "collection"
    COMMAND_AND_CONTROL = "command-and-control"
    EXFILTRATION = "exfiltration"
    IMPACT = "impact"


class MitreTechnique(BaseModel):
    """Definition of a specific MITRE ATT&CK technique or sub-technique."""
    technique_id: str = Field(..., description="MITRE Technique ID (e.g. T1059.001)")
    name: str = Field(..., description="Technique name (e.g. PowerShell)")
    tactic: MitreTactic = Field(..., description="Associated tactic category")
    description: str = Field(default="", description="Technique summary")


class LogEvent(BaseModel):
    """A single security or sysmon telemetry log event."""
    id: int = Field(..., description="Unique event identifier")
    timestamp: str = Field(..., description="ISO timestamp of the event")
    event_id: int = Field(..., description="Windows Event ID (e.g. 1=Process Create, 3=Network, 4104=ScriptBlock)")
    source: str = Field(default="Microsoft-Windows-Sysmon/Operational", description="Log channel/provider")
    host: str = Field(default="CORP-WKSTN-01", description="Hostname")
    user: str = Field(default="NT AUTHORITY\\SYSTEM", description="User or Account name")
    process_name: str = Field(default="", description="Executable name (e.g. powershell.exe)")
    command_line: str = Field(default="", description="Full process command line arguments")
    parent_process: str = Field(default="", description="Parent executable name")
    parent_command_line: str = Field(default="", description="Parent command line")
    process_id: Optional[int] = Field(default=None, description="PID")
    parent_process_id: Optional[int] = Field(default=None, description="PPID")
    ip_address: Optional[str] = Field(default=None, description="Destination or source IP")
    port: Optional[int] = Field(default=None, description="Destination or source port")
    file_path: Optional[str] = Field(default=None, description="Target file path")
    registry_path: Optional[str] = Field(default=None, description="Target registry key/value")
    details: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary raw event fields")
    is_malicious: bool = Field(default=False, description="Ground truth label: true if part of attack")
    ground_truth_rule: Optional[str] = Field(default=None, description="Sigma rule or attack procedure ID")


class GroundTruthDetection(BaseModel):
    """Expected malicious activity defined in benchmark ground truth."""
    rule_id: str = Field(..., description="Identifier for the ground truth rule (e.g. SIGMA-T1059-001)")
    tactic: MitreTactic = Field(..., description="Associated MITRE tactic")
    technique_id: str = Field(..., description="Technique ID (e.g. T1059.001)")
    technique_name: str = Field(..., description="Technique name")
    matched_event_ids: List[int] = Field(default_factory=list, description="IDs of matching log events")
    indicator_summary: str = Field(..., description="Summary of the malicious indicator")
    severity: str = Field(default="HIGH", description="Severity level: CRITICAL, HIGH, MEDIUM, LOW")


class AgentDetection(BaseModel):
    """Threat detection submitted by an agent during its investigation."""
    tactic: MitreTactic = Field(..., description="Identified MITRE tactic")
    technique_id: str = Field(..., description="Identified Technique ID")
    technique_name: str = Field(..., description="Technique name")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Agent's confidence score")
    evidence_event_ids: List[int] = Field(default_factory=list, description="Log event IDs cited as proof")
    explanation: str = Field(..., description="Agent's forensic explanation of the threat")
    query_used: Optional[str] = Field(default=None, description="SQL query that surfaced this finding")
    is_true_positive: Optional[bool] = Field(default=None, description="Verification result against ground truth")
    matched_ground_truth_rule: Optional[str] = Field(default=None, description="Matching ground truth rule ID")


class HuntStep(BaseModel):
    """A single reasoning/action step within the agent's investigation trajectory."""
    step_index: int = Field(..., description="Step sequence number")
    agent_role: str = Field(default="Threat Hunter", description="Active subagent or agent role")
    thought: str = Field(default="", description="Internal reasoning / thinking thoughts from Gemini 3.7 Flash")
    action_type: str = Field(..., description="Action taken (e.g., 'sql_query', 'correlate_process', 'classify_mitre', 'submit_findings')")
    sql_query: Optional[str] = Field(default=None, description="SQL query executed against telemetry DB")
    tool_output: Optional[str] = Field(default=None, description="Output or table result returned by the environment")
    new_findings: List[AgentDetection] = Field(default_factory=list, description="Detections discovered in this step")
    duration_ms: float = Field(default=0.0, description="Step duration in milliseconds")


class AgentTrajectory(BaseModel):
    """Complete record of an agent's multi-step investigation."""
    agent_name: str = Field(..., description="Harness name (e.g. Antigravity, Open Code)")
    model_name: str = Field(default="gemini-3.7-flash", description="Underlying LLM model")
    thinking_budget: int = Field(default=2048, description="Thinking token budget allocated")
    total_steps: int = Field(default=0, description="Total reasoning/execution steps taken")
    total_queries: int = Field(default=0, description="Number of SQL queries executed")
    total_tokens_used: int = Field(default=0, description="Estimated total tokens consumed")
    execution_time_seconds: float = Field(default=0.0, description="Wall-clock runtime in seconds")
    steps: List[HuntStep] = Field(default_factory=list, description="Ordered timeline of hunting steps")
    detected_threats: List[AgentDetection] = Field(default_factory=list, description="All detected threats")
    investigation_summary: str = Field(default="", description="Final incident summary compiled by agent")


class ScenarioTask(BaseModel):
    """A cybersecurity threat-hunting scenario task."""
    id: str = Field(..., description="Unique scenario ID (e.g. simbian-apt29-01)")
    title: str = Field(..., description="Scenario title")
    description: str = Field(..., description="High-level scenario context")
    attack_family: str = Field(..., description="Attack campaign or category (e.g. APT29, Ransomware, WMI-Pivot)")
    difficulty: str = Field(default="Medium", description="Difficulty: Easy, Medium, Hard, APT-MultiStage")
    initial_alert: str = Field(..., description="Initial SOC triage alert or lead provided to the agent")
    tactics_present: List[MitreTactic] = Field(default_factory=list, description="MITRE tactics present in scenario")
    total_events: int = Field(default=0, description="Count of log events in the telemetry dataset")
    ground_truth_detections: List[GroundTruthDetection] = Field(default_factory=list, description="Expected findings")
    events: List[LogEvent] = Field(default_factory=list, description="Raw telemetry logs for this scenario")


class TacticScore(BaseModel):
    """Evaluation score breakdown for a specific MITRE ATT&CK tactic."""
    tactic: MitreTactic
    ground_truth_count: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    recall: float = 0.0
    precision: float = 0.0
    f1_score: float = 0.0
    passed_simbian_bar: bool = False  # Simbian requires >= 50% recall


class EvaluationMetricResult(BaseModel):
    """Aggregate evaluation metrics according to Simbian Cyber Defense Benchmark standards."""
    scenario_id: str
    agent_name: str
    model_name: str
    thinking_budget: int
    tactic_scores: Dict[str, TacticScore] = Field(default_factory=dict)
    overall_recall: float = 0.0
    overall_precision: float = 0.0
    overall_f1: float = 0.0
    mitre_chain_coverage: float = 0.0  # Percentage of tactics detected
    query_efficiency_score: float = 0.0  # Detections per query
    false_discovery_rate: float = 0.0  # FP / (TP + FP)
    simbian_pass_status: bool = False  # True if recall >= 50% on EVERY present tactic
    summary_verdict: str = ""


class EvalRunSummary(BaseModel):
    """Full bundle containing scenario, configuration, trajectory, and graded evaluation."""
    run_id: str
    timestamp: str
    scenario_id: str
    scenario_title: str
    agent_harness: str
    model_name: str
    thinking_budget: int
    harbor_sandbox_mode: str = "local-isolated"
    benchhub_slice: str = "all-tactics"
    metrics: EvaluationMetricResult
    trajectory: AgentTrajectory
