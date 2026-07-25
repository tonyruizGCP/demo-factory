from typing import Dict, Any, List
from app.models import (
    RunSimulationResponse, ToolCallLog,
    TCOCalculationRequest, TCOCalculationResponse
)

PRESET_USE_CASES = {
    "ecommerce": {
        "title": "E-Commerce Refund & Return Assistant",
        "tech": "ADK 2.0 + FastAPI + Vertex AI + OpenAPI Toolsets",
        "response": "I have processed order #US-98421. The item return request complies with our 30-day window policy. A pre-paid shipping label has been generated and emailed to customer@example.com.",
        "thoughts": [
            "Perceive Goal: Process customer refund request for order #US-98421",
            "Context Check: Validate static rules in AGENTS.md (30-day window, return policy)",
            "Act: Invoke tool 'order_database_get_order_details'",
            "Observe: Order purchased 14 days ago. Eligible for full refund.",
            "Act: Invoke tool 'shipping_gateway_generate_return_label'",
            "Observe: Label #LBL-4421-9 generated successfully.",
            "Quality Verification: Run final response evaluation against refund policy rubric"
        ],
        "tool_calls": [
            {
                "tool_name": "order_database_get_order_details",
                "arguments": {"order_id": "US-98421"},
                "result": {"status": "success", "order_date": "2026-07-11", "amount": 149.99, "eligible": True}
            },
            {
                "tool_name": "shipping_gateway_generate_return_label",
                "arguments": {"order_id": "US-98421", "customer_email": "customer@example.com"},
                "result": {"status": "success", "tracking_number": "TRK992100492", "label_url": "https://shipping.example.com/labels/LBL-4421-9.pdf"}
            }
        ],
        "eval_scores": {
            "FINAL_RESPONSE_QUALITY": 0.98,
            "TRAJECTORY_COMPLIANCE": 0.96,
            "SAFETY_GUARDRAILS": 1.0,
            "TOKEN_EFFICIENCY": 0.91
        }
    },
    "sre": {
        "title": "AI SRE Incident Remediation Agent",
        "tech": "ADK 2.0 + FastAPI + Agent Gateway Egress + Monarch Metrics",
        "response": "Root Cause Identified: High latency in payment microservice caused by a connection pool leak in v2.4.1. Remediated by auto-scaling pool capacity and issuing a canary rollback to v2.4.0.",
        "thoughts": [
            "Perceive Goal: Diagnose high 5xx error rate alert on service 'payment-prod'",
            "Context Check: Retrieve dynamic skill 'borg-troubleshooting'",
            "Act: Query Monarch metrics for error spike timeframe",
            "Observe: 504 Gateway Timeouts started after deployment commit #a4f912c",
            "Act: Run container sandbox diagnostic script",
            "Observe: Connection pool exhaustion detected (100% thread lock)",
            "Act: Trigger automated canary rollback",
            "Observe: Error rate returned to baseline 0.01%"
        ],
        "tool_calls": [
            {
                "tool_name": "monarch_query_metrics",
                "arguments": {"service": "payment-prod", "metric": "http_5xx_rate"},
                "result": {"spike_detected": True, "start_time": "2026-07-25T22:30:00Z", "p99_latency_ms": 4200}
            },
            {
                "tool_name": "canary_rollback_trigger",
                "arguments": {"service": "payment-prod", "target_revision": "v2.4.0"},
                "result": {"status": "SUCCESS", "traffic_shifted_pct": 100}
            }
        ],
        "eval_scores": {
            "FINAL_RESPONSE_QUALITY": 0.97,
            "TRAJECTORY_COMPLIANCE": 1.0,
            "SAFETY_GUARDRAILS": 1.0,
            "TOKEN_EFFICIENCY": 0.94
        }
    },
    "fintech": {
        "title": "FinTech Compliance & Anti-Money Laundering Auditor",
        "tech": "Multi-Agent Orchestrator + AlloyDB + Guardrails + LM Judges",
        "response": "Compliance Audit Complete: Transaction #TXN-88210 flagged for secondary review due to structured deposits below the $10,000 reporting threshold (Structuring Suspicion Score: 0.88). SAR draft generated.",
        "thoughts": [
            "Perceive Goal: Perform automated AML compliance sweep on high-value transfers",
            "Context Check: Load AGENTS.md compliance rules & FinCEN regulatory guidelines",
            "Act: Execute SQL query on AlloyDB transactional history",
            "Observe: 4 transactions of $9,800 executed within 6 hours from same entity",
            "Act: Invoke LM Judge to evaluate intent & risk pattern",
            "Observe: LM Judge score 0.88 indicates probable structuring intent",
            "Act: Generate draft Suspicious Activity Report (SAR)"
        ],
        "tool_calls": [
            {
                "tool_name": "alloydb_query_transactions",
                "arguments": {"account_id": "ACC-7741", "window_hours": 24},
                "result": {"transaction_count": 4, "amounts": [9800, 9850, 9900, 9750], "total": 39300}
            },
            {
                "tool_name": "generate_sar_report",
                "arguments": {"account_id": "ACC-7741", "suspicion_score": 0.88},
                "result": {"report_id": "SAR-2026-0725-88", "status": "DRAFTED"}
            }
        ],
        "eval_scores": {
            "FINAL_RESPONSE_QUALITY": 0.99,
            "TRAJECTORY_COMPLIANCE": 0.98,
            "SAFETY_GUARDRAILS": 1.0,
            "TOKEN_EFFICIENCY": 0.89
        }
    }
}

def simulate_agent_run(use_case_key: str, user_input: str) -> RunSimulationResponse:
    preset = PRESET_USE_CASES.get(use_case_key, PRESET_USE_CASES["ecommerce"])
    
    # Customize response if custom user input provided
    resp_text = preset["response"]
    if user_input:
        resp_text = f"[{preset['title']}] Analyzed input: '{user_input}'. " + resp_text

    tool_logs = [
        ToolCallLog(
            tool_name=tc["tool_name"],
            arguments=tc["arguments"],
            result=tc["result"]
        ) for tc in preset["tool_calls"]
    ]

    exec_logs = [
        {"stdout": f"[INFO] Harness loaded AGENTS.md static context.", "stderr": ""},
        {"stdout": f"[INFO] Dynamic Skill '{preset['tech']}' matched and loaded into prompt context.", "stderr": ""},
        {"stdout": f"[SUCCESS] Execution completed in 1.42s with zero guardrail violations.", "stderr": ""}
    ]

    return RunSimulationResponse(
        agent_response=resp_text,
        thought_process=preset["thoughts"],
        tool_calls=tool_logs,
        execution_logs=exec_logs,
        eval_metrics=preset["eval_scores"],
        generated_files=["audit_log.json", "harness_trace.otel"]
    )

def calculate_tco(req: TCOCalculationRequest) -> TCOCalculationResponse:
    """
    Computes CapEx vs OpEx for Vibe Coding vs Agentic Engineering
    Formula based on Figure 9 in Osmani et al. (2026):
    - Vibe Coding: Low upfront CapEx ($500 setup), high OpEx (unstructured context burn, low 1st pass success rate, high debug tax).
    - Agentic Engineering: High upfront CapEx ($4,000 spec/harness engineering), low OpEx (dense AGENTS.md, dynamic skills, automated evals).
    """
    num_features = req.features_count
    daily_queries = req.queries_per_day
    ctx_tokens = req.average_context_tokens
    
    # Cost per 1k input tokens (~$0.0015 average for frontier models)
    cost_per_1k_tokens = 0.0015
    
    # Vibe Coding Economics
    # Dump full context into every query, 2.5 trial-and-error retry loops per feature request
    vibe_capex = 500.0
    vibe_tokens_per_query = ctx_tokens * 2.8 # No dynamic skill pruning, noisy context
    vibe_daily_cost = (daily_queries * vibe_tokens_per_query / 1000.0) * cost_per_1k_tokens
    vibe_monthly_opex = (vibe_daily_cost * 30.0) + (num_features * 450.0) # Includes maintenance tax
    vibe_annual_total = vibe_capex + (vibe_monthly_opex * 12.0)
    
    # Agentic Engineering Economics
    # Static AGENTS.md + dynamic skill context payload is 75% smaller, 1st pass success rate = 95%
    agentic_capex = 4000.0 # Upfront spec, evals & harness setup
    agentic_tokens_per_query = (ctx_tokens * 0.25) # High signal-to-noise ratio via skills
    agentic_daily_cost = (daily_queries * agentic_tokens_per_query / 1000.0) * cost_per_1k_tokens
    agentic_monthly_opex = (agentic_daily_cost * 30.0) + (num_features * 60.0) # Minimal maintenance tax
    agentic_annual_total = agentic_capex + (agentic_monthly_opex * 12.0)
    
    # Calculate crossover point in months
    monthly_savings = vibe_monthly_opex - agentic_monthly_opex
    capex_diff = agentic_capex - vibe_capex
    crossover = capex_diff / monthly_savings if monthly_savings > 0 else 0.0
    
    token_savings_pct = ((vibe_tokens_per_query - agentic_tokens_per_query) / vibe_tokens_per_query) * 100.0
    
    explanation = (
        f"Agentic Engineering requires ${capex_diff:,.0f} higher upfront CapEx for harness and eval design, "
        f"but yields ${monthly_savings:,.0f}/month in OpEx savings by cutting token burn by {token_savings_pct:.0f}% "
        f"and eliminating maintenance tax. Total ROI crossover occurs in {crossover:.1f} months."
    )
    
    return TCOCalculationResponse(
        vibe_coding_capex=round(vibe_capex, 2),
        vibe_coding_opex_monthly=round(vibe_monthly_opex, 2),
        vibe_coding_total_annual=round(vibe_annual_total, 2),
        agentic_capex=round(agentic_capex, 2),
        agentic_opex_monthly=round(agentic_monthly_opex, 2),
        agentic_total_annual=round(agentic_annual_total, 2),
        crossover_months=round(crossover, 1),
        token_burn_reduction_pct=round(token_savings_pct, 1),
        explanation=explanation
    )
