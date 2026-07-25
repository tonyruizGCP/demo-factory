from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class GenerateDemoRequest(BaseModel):
    customer_use_case: str = Field(..., json_schema_extra={"example": "E-Commerce Customer Support & Returns Bot"})
    tech_approach: str = Field(..., json_schema_extra={"example": "ADK 2.0 + FastAPI + Vertex AI + MCP"})
    rigor_level: str = Field("agentic_engineering", json_schema_extra={"example": "agentic_engineering"}) # agentic_engineering, structured, vibe_coding
    include_evals: bool = True
    include_ci_cd: bool = True
    project_slug: Optional[str] = None

class GeneratedHarnessResponse(BaseModel):
    project_name: str
    project_path: str
    status: str
    agents_md_content: str
    files_created: List[str]
    eval_rubrics: Dict[str, Any]
    ci_workflow_yaml: str
    tco_summary: Dict[str, Any]

class EvalRunRequest(BaseModel):
    project_slug: str

class EvalMetricResult(BaseModel):
    metric_name: str
    score: float
    max_score: float = 1.0
    passed: bool
    explanation: str

class EvalRunResult(BaseModel):
    project_slug: str
    overall_passed: bool
    deterministic_score: float
    trajectory_score: float
    lm_judge_score: float
    metrics: List[EvalMetricResult]
    logs: List[str]

class RunSimulationRequest(BaseModel):
    use_case: str
    user_input: str
    session_id: Optional[str] = "demo_session_1"

class ToolCallLog(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]

class RunSimulationResponse(BaseModel):
    agent_response: str
    thought_process: List[str]
    tool_calls: List[ToolCallLog]
    execution_logs: List[Dict[str, str]]
    eval_metrics: Dict[str, Any]
    generated_files: List[str]

class TCOCalculationRequest(BaseModel):
    features_count: int = Field(10, ge=1, le=100)
    queries_per_day: int = Field(500, ge=10, le=100000)
    average_context_tokens: int = Field(15000, ge=1000, le=200000)

class TCOCalculationResponse(BaseModel):
    vibe_coding_capex: float
    vibe_coding_opex_monthly: float
    vibe_coding_total_annual: float
    agentic_capex: float
    agentic_opex_monthly: float
    agentic_total_annual: float
    crossover_months: float
    token_burn_reduction_pct: float
    explanation: str
