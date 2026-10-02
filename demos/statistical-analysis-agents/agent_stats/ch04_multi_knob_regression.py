"""Chapter 4: Multi-Knob Attribution & Multiple Regression.

Implements:
- Synthetic Benchmark Data Generator across 3 continuous agent harness knobs:
  * `thinking_budget` (100 to 4000 tokens)
  * `context_chunks` (1 to 20 chunks)
  * `tool_timeout` (5 to 60 seconds)
  with linear gains, quadratic decay (overthinking / context rot), and synergy
  interaction (`thinking_budget * context_chunks`).
- Second-Order Response Surface Regression via `statsmodels.formula.api.ols`.
- Plain-English Developer Interpretation Extractor (stationary point, marginal
  degradation past optimum, and interaction effect).
"""

from __future__ import annotations

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.regression.linear_model import RegressionResultsWrapper


def generate_multi_knob_dataset(
    n_samples: int = 300, random_state: int = 42
) -> pd.DataFrame:
    """Generate synthetic benchmark runs varying 3 continuous agent harness knobs.

    True response surface mechanism:
    - `thinking_budget` (100..4000): rises up to ~2500 tokens, then quadratic decay
      due to overthinking / reasoning loops.
    - `context_chunks` (1..20): rises up to ~12 chunks, then decays due to
      context distraction ("lost in the middle").
    - Interaction `thinking_budget * context_chunks`: retrieving more context chunks
      requires higher thinking budget to synthesize effectively.
    - `tool_timeout` (5..60s): modest logarithmic/linear gain that plateaus quickly.
    """
    rng = np.random.default_rng(random_state)

    thinking_budget = rng.uniform(100.0, 4000.0, size=n_samples)
    context_chunks = rng.uniform(1.0, 20.0, size=n_samples)
    tool_timeout = rng.uniform(5.0, 60.0, size=n_samples)

    # Scaled units for clean interpretability:
    # T = thinking_budget / 1000.0 (in thousands of tokens, 0.1 to 4.0)
    # C = context_chunks (1 to 20)
    # S = tool_timeout (5 to 60)
    t_k = thinking_budget / 1000.0

    true_score = (
        0.34
        + 0.255 * t_k
        - 0.056 * (t_k**2)
        + 0.024 * context_chunks
        - 0.00125 * (context_chunks**2)
        + 0.0042 * (t_k * context_chunks)
        + 0.0009 * tool_timeout
    )
    noise = rng.normal(0.0, 0.022, size=n_samples)
    pass_rate = np.clip(true_score + noise, 0.05, 0.98)

    return pd.DataFrame(
        {
            "thinking_budget": thinking_budget,
            "context_chunks": context_chunks,
            "tool_timeout": tool_timeout,
            "pass_rate": pass_rate,
        }
    )


def fit_response_surface_model(df: pd.DataFrame) -> RegressionResultsWrapper:
    """Fit a second-order polynomial + interaction OLS model using statsmodels Formula API."""
    formula = (
        "pass_rate ~ thinking_budget + I(thinking_budget**2) "
        "+ context_chunks + I(context_chunks**2) "
        "+ thinking_budget:context_chunks "
        "+ tool_timeout"
    )
    model = smf.ols(formula=formula, data=df).fit()
    return model


def extract_developer_insights(model: RegressionResultsWrapper) -> Dict[str, object]:
    """Compute analytical optimum and plain-English engineering takeaways from OLS params."""
    p = model.params
    b_t = float(p["thinking_budget"])
    b_t2 = float(p["I(thinking_budget ** 2)"])
    b_c = float(p["context_chunks"])
    b_c2 = float(p["I(context_chunks ** 2)"])
    b_tc = float(p["thinking_budget:context_chunks"])
    b_time = float(p["tool_timeout"])

    # Solve 2x2 linear system for stationary point (d/dT = 0, d/dC = 0):
    # 2*b_t2*T + b_tc*C = -b_t
    # b_tc*T + 2*b_c2*C = -b_c
    a_mat = np.array([[2.0 * b_t2, b_tc], [b_tc, 2.0 * b_c2]])
    rhs = np.array([-b_t, -b_c])
    opt_t, opt_c = np.linalg.solve(a_mat, rhs)
    opt_t = float(np.clip(opt_t, 100.0, 4000.0))
    opt_c = float(np.clip(opt_c, 1.0, 20.0))

    # Marginal slope d(pass_rate)/d(thinking_budget) at 3,200 tokens (with C=10 chunks)
    ref_chunks = 10.0
    opt_t_at_ref = -(b_t + b_tc * ref_chunks) / (2.0 * b_t2)
    slope_at_3500_per_100 = (b_t + 2.0 * b_t2 * 3500.0 + b_tc * ref_chunks) * 100.0

    # Loss from overthinking: going from opt_t_at_ref (~2600) to 4000 tokens at C=10
    pred_df = pd.DataFrame(
        {
            "thinking_budget": [opt_t_at_ref, 4000.0],
            "context_chunks": [ref_chunks, ref_chunks],
            "tool_timeout": [30.0, 30.0],
        }
    )
    preds = model.predict(pred_df).to_numpy()
    overthinking_drop = float(preds[0] - preds[1])
    avg_loss_per_100_past_opt = (
        overthinking_drop / ((4000.0 - opt_t_at_ref) / 100.0)
    ) * 100.0

    insights = [
        (
            f"1. Optimal Thinking Budget (at {int(ref_chunks)} context chunks): "
            f"~{opt_t_at_ref:,.0f} tokens (Global joint optimum: {opt_t:,.0f} tokens, "
            f"{opt_c:.1f} chunks)."
        ),
        (
            f"2. Overthinking Penalty: Increasing thinking_budget beyond {opt_t_at_ref:,.0f} "
            f"up to 4,000 tokens reduces pass rate by {overthinking_drop*100:.2f} percentage points "
            f"(an average efficiency loss of {avg_loss_per_100_past_opt:.2f}% per 100 extra tokens; "
            f"instantaneous slope at 3,500 tokens is {slope_at_3500_per_100*100:+.2f}% per 100 tokens)."
        ),
        (
            f"3. Context-Thinking Synergy: The interaction term (p = {model.pvalues['thinking_budget:context_chunks']:.2e}) "
            f"shows each additional context chunk adds +{b_tc*1000*100:.2f} pp more value per 1,000 thinking tokens."
        ),
        (
            f"4. Tool Timeout Effect: Each +10s of tool_timeout yields +{b_time*10*100:.2f} pp "
            f"(p = {model.pvalues['tool_timeout']:.2e}), a minor linear effect compared to reasoning & retrieval tuning."
        ),
    ]

    return {
        "optimal_thinking_budget": opt_t,
        "optimal_context_chunks": opt_c,
        "optimal_thinking_at_10_chunks": float(opt_t_at_ref),
        "loss_per_100_tokens_past_optimum_pct": float(avg_loss_per_100_past_opt),
        "r_squared": float(model.rsquared),
        "adj_r_squared": float(model.rsquared_adj),
        "plain_english_insights": insights,
    }
