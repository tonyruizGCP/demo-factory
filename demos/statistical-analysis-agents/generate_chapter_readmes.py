"""Generates per-chapter directories, short README.md descriptions, and syncs notebooks/scripts."""

from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
CHAPTERS_DIR = ROOT / "chapters"

CHAPTER_SPECS = [
    {
        "slug": "01_stochasticity_trap",
        "title": "Chapter 1: The Stochasticity Trap (`Pass@k` vs. `Pass^k`)",
        "module": "agent_stats/ch01_stochasticity.py",
        "figure": "ch01_pass_at_k_vs_pass_pow_k.png",
        "summary": (
            "Explores execution variance across repeated evaluation seeds and contrasts "
            "the optimistic capability metric (`Pass@k`, at least 1 of `k` trials succeeds) "
            "against the production consistency metric (`Pass^k`, all `k` trials succeed)."
        ),
        "math": r"""- **Unbiased $\text{Pass}@k$ Estimator (Chen et al., 2021)**:
  $$\widehat{\text{Pass}@k} = 1 - \frac{\binom{n - c}{k}}{\binom{n}{k}}$$
- **Unbiased $\text{Pass}^k$ Consistency Estimator ($\tau$-bench, Yao et al., 2024)**:
  $$\widehat{\text{Pass}^k} = \frac{\binom{c}{k}}{\binom{n}{k}}, \qquad \widehat{\text{Pass}^k}_{\text{plugin}} = \left(\frac{c}{n}\right)^k$$""",
        "highlights": [
            "`AgentStochasticitySimulator`: Simulates $N=200$ tasks over $n=20$ seeds with controllable baseline capability and execution noise.",
            "**Visualizations**: $\\text{Pass}@k$ vs. $\\text{Pass}^k$ curves ($k=1\\dots 10$) and a $7 \\times 7$ **Consistency Delta Heatmap** ($\\text{Pass}@1 - \\text{Pass}^5$).",
            "**Hands-on Prompt Audit**: Demonstrates how a single-seed $\\text{Pass}@1$ run mistakenly selects a flaky prompt (76% $\\text{Pass}@1$, **26% $\\text{Pass}^5$**) over a production-grade deterministic prompt (74% $\\text{Pass}@1$, **66% $\\text{Pass}^5$**).",
        ],
    },
    {
        "slug": "02_data_hygiene_and_overfitting",
        "title": "Chapter 2: Data Hygiene & Overfitting Prevention",
        "module": "agent_stats/ch02_hygiene_overfitting.py",
        "figure": "ch02_goodharts_law_holdout_gate.png",
        "summary": (
            "Demonstrates Goodhart's Law ('when a measure becomes a target, it ceases to be a good measure') "
            "during iterative agent prompt hill-climbing, and implements a stratified `HoldoutGate` to block "
            "reward-hacking mutations."
        ),
        "math": r"""- **Joint Stratification Condition**:
  $$\mathbb{P}(D = d, C = c \mid \mathcal{D}_{\text{opt}}) = \mathbb{P}(D = d, C = c \mid \mathcal{D}_{\text{hold}})$$
  across Difficulty Tiers (`Easy`, `Medium`, `Hard`) $\times$ Capability Tags (`tool_selection`, `context_retrieval`, `code_execution`).
- **Holdout Gate Acceptance Rule**:
  $$\Delta \hat{R}_{\text{opt}} \ge \tau_{\text{opt}} \quad \wedge \quad \Delta \hat{R}_{\text{hold}} \ge 0 \quad \wedge \quad (\hat{R}_{\text{opt}} - \hat{R}_{\text{hold}}) \le \gamma_{\max}$$""",
        "highlights": [
            "Generates 200 synthetic benchmark tasks across 9 difficulty $\\times$ capability strata and splits them 60% Optimization ($n=120$) / 40% Holdout ($n=80$).",
            "Simulates 30 sequential prompt mutations mixing genuine capability improvements with benchmark-quirk reward hacking.",
            "Pinpoints the exact **Overfitting Divergence Step** where ungated optimization climbs to >90% on the Optimization set while collapsing to ~52% on unseen Holdout tasks.",
        ],
    },
    {
        "slug": "03_frequentist_ab_testing",
        "title": "Chapter 3: Frequentist A/B Testing & Power Analysis",
        "module": "agent_stats/ch03_frequentist_ab.py",
        "figure": "ch03_mcnemar_power_and_wilcoxon.png",
        "summary": (
            "Implements rigorous paired A/B testing (`McNemar's Test` for binary pass/fail outcomes and "
            "`Wilcoxon Signed-Rank Test` for skewed token/latency metrics) alongside statistical power analysis."
        ),
        "math": r"""- **McNemar's Paired Test with Edwards' Continuity Correction**:
  $$\chi^2_{\text{McNemar}} = \frac{(|b - c| - 1)^2}{b + c} \sim \chi^2_1$$
  where $b$ is the count of regressions (Baseline Pass, Candidate Fail) and $c$ is the count of newly solved tasks (Baseline Fail, Candidate Pass).
- **Paired Sample Size Reduction**: Conditioning on identical tasks cancels shared task-difficulty variance, shrinking discordant proportion $\psi = p_b + p_c$.""",
        "highlights": [
            "`calculate_required_sample_size`: Computes required task counts for both unpaired 2-sample $Z$-tests and paired McNemar tests.",
            "**1,000-Trial Monte Carlo Power Benchmark**: Proves that detecting a $+5\\%$ pass rate lift ($65\\% \\to 70\\%$) at $80\\%$ power requires **~145 paired tasks** with McNemar's test versus **~1,375 tasks per arm** with an unpaired $Z$-test (**9.5x sample reduction**).",
            "Applies the non-parametric **Wilcoxon Signed-Rank Test** to heavy-tailed log-normal token consumption distributions.",
        ],
    },
    {
        "slug": "04_multi_knob_attribution",
        "title": "Chapter 4: Multi-Knob Attribution & Multiple Regression",
        "module": "agent_stats/ch04_multi_knob_regression.py",
        "figure": "ch04_multi_knob_response_surface.png",
        "summary": (
            "Fits a second-order polynomial response surface (`statsmodels` Formula OLS) across three continuous "
            "agent harness knobs (`thinking_budget`, `context_chunks`, `tool_timeout`) to isolate linear gains, "
            "quadratic overthinking decay, and parameter interaction synergies."
        ),
        "math": r"""- **Second-Order Response Surface Model**:
  $$\text{PassRate} = \beta_0 + \beta_T T + \beta_{T^2} T^2 + \beta_C C + \beta_{C^2} C^2 + \beta_{TC}(T \cdot C) + \beta_S S + \epsilon$$
- **Stationary Optimum $(T^*, C^*)$**:
  $$\begin{bmatrix} 2\beta_{T^2} & \beta_{TC} \\ \beta_{TC} & 2\beta_{C^2} \end{bmatrix} \begin{bmatrix} T^* \\ C^* \end{bmatrix} = \begin{bmatrix} -\beta_T \\ -\beta_C \end{bmatrix}$$""",
        "highlights": [
            "Fits a full quadratic + interaction OLS regression ($R^2 = 0.94$) with $t$-statistics, $p$-values, and confidence intervals.",
            "Renders 3D surface plots and 2D iso-performance contour maps pinpointing the stationary optimum (~2,690 thinking tokens, ~14.1 context chunks).",
            "Automatically extracts plain-English developer insights quantifying the marginal efficiency loss per 100 tokens past the overthinking threshold.",
        ],
    },
    {
        "slug": "05_bayesian_sequential_testing",
        "title": "Chapter 5: Bayesian Sequential Testing & Early Stopping",
        "module": "agent_stats/ch05_bayesian_sequential.py",
        "figure": "ch05_bayesian_sequential_stopping.png",
        "summary": (
            "Implements conjugate Beta-Binomial posterior updating and sequential early stopping (`BetaBinomialEvaluator`) "
            "to prune weak prompt candidates early and accept strong winners without running fixed $N=500$ sweeps."
        ),
        "math": r"""- **Closed-Form Conjugate Posterior Update**:
  $$\theta \mid (s, n) \sim \text{Beta}(\alpha_0 + s, \, \beta_0 + n - s)$$
- **Posterior Probability of Superiority**:
  $$P(\theta_{\text{cand}} > \theta_{\text{base}} \mid D) = \int_0^1 f_{\text{Beta}}(x; \alpha_C, \beta_C) F_{\text{Beta}}(x; \alpha_B, \beta_B) \, dx$$""",
        "highlights": [
            "Computes $P(\\theta_{\\text{cand}} > \\theta_{\\text{base}} \\mid D)$ via both **exact 1D numerical quadrature** (`scipy.integrate.quad`) and **Monte Carlo sampling** (`numpy`).",
            "`BetaBinomialEvaluator`: Stateful step-by-step evaluator with configurable boundaries (`ACCEPT` at $P \\ge 0.95$, `ABANDON` at $P \\le 0.10$, else `CONTINUE`).",
            "**Compute-Savings Benchmark**: Across 100 weak variants and 10 strong variants, Bayesian early stopping reduces total evaluation trials by **~74%** compared to fixed $N=500$ sweeps.",
        ],
    },
    {
        "slug": "06_hierarchical_bayesian_modeling",
        "title": "Chapter 6: Hierarchical Bayesian Modeling for Edge Cases",
        "module": "agent_stats/ch06_hierarchical_bayes.py",
        "figure": "ch06_hierarchical_forest_plot.png",
        "summary": (
            "Demonstrates Empirical Bayes partial pooling and shrinkage across 8 agent failure categories with "
            "uneven sample sizes ($N_j \\in [3, 150]$), preventing false regression panic on sparse edge-case slices."
        ),
        "math": r"""- **Hierarchical Beta-Binomial Model**:
  $$\theta_j \sim \text{Beta}(\alpha_0, \beta_0), \qquad S_j \mid \theta_j \sim \text{Binomial}(N_j, \theta_j)$$
- **Posterior Shrinkage Estimator**:
  $$\mathbb{E}[\theta_j \mid S_j, N_j] = \underbrace{\left(\frac{\kappa}{\kappa + N_j}\right)}_{B_j} \mu_0 + (1 - B_j)\left(\frac{S_j}{N_j}\right), \qquad \kappa = \alpha_0 + \beta_0$$""",
        "highlights": [
            "Compares **No Pooling** ($S_j/N_j$), **Complete Pooling** ($\\sum S_j / \\sum N_j$), and **Partial Pooling** (Empirical Bayes marginal likelihood maximization).",
            "Demonstrates how `distributed_race_condition` ($N=3, S=0$, raw $0.0\\%$) and `memory_leak` ($N=4, S=1$, raw $25.0\\%$) are shrunk toward the population hyperprior mean ($56.8\\%$ and $59.9\\%$).",
            "Reduces category pass-rate estimation RMSE against true latent capability by **68%** compared to raw unpooled proportions.",
        ],
    },
    {
        "slug": "07_bayesian_optimization",
        "title": "Chapter 7: Bayesian Optimization with Gaussian Processes",
        "module": "agent_stats/ch07_bayesian_optimization.py",
        "figure": "ch07_bayesian_optimization_surfaces.png",
        "summary": (
            "Uses Gaussian Process Regression (`Matern(nu=2.5)` kernel) and acquisition functions (`Expected Improvement` "
            "and `GP-UCB`) to find the global optimum of an expensive black-box agent harness within 25 trials."
        ),
        "math": r"""- **Matérn $5/2$ Covariance Kernel**:
  $$k_{5/2}(r) = \sigma_f^2 \left(1 + \sqrt{5}r + \frac{5}{3}r^2\right)\exp(-\sqrt{5}r)$$
- **Expected Improvement (EI) & GP-UCB**:
  $$\text{EI}(\mathbf{x}) = (\mu(\mathbf{x}) - y^+ - \xi)\Phi(Z) + \sigma(\mathbf{x})\phi(Z), \qquad \text{UCB}(\mathbf{x}) = \mu(\mathbf{x}) + \kappa\sigma(\mathbf{x})$$""",
        "highlights": [
            "Models the multimodal black-box objective `evaluate_harness_config(reasoning_tokens, context_limit)` using `scikit-learn` `GaussianProcessRegressor`.",
            "Iteratively balances exploration (high posterior uncertainty $\\sigma$) and exploitation (high posterior mean $\\mu$) over 25 evaluations.",
            "Renders side-by-side GP Posterior Mean/Uncertainty contours and Expected Improvement acquisition surfaces at Trials 5, 12, and 25.",
        ],
    },
    {
        "slug": "08_failure_trace_clustering",
        "title": "Chapter 8: Failure Trace Mining & Unsupervised Clustering",
        "module": "agent_stats/ch08_trace_clustering.py",
        "figure": "ch08_failure_trace_clusters.png",
        "summary": (
            "Parses 300 raw agent failure logs (`stdout`/`stderr`, tool payloads, stack traces), vectorizes them "
            "with sublinear TF-IDF, clusters failure modes via PCA + $k$-Means, and synthesizes actionable System Prompt "
            "Negative Constraints."
        ),
        "math": r"""- **Sublinear TF-IDF Vectorization**:
  $$\text{tfidf}(t, d) = (1 + \log \text{tf}(t, d)) \cdot \left(\log \frac{1 + N}{1 + \text{df}(t)} + 1\right)$$
- **Cluster Medoid Trace Selection**:
  $$\text{medoid}(k) = \arg\min_{i \in C_k} \|\mathbf{v}_i - \boldsymbol{\mu}_k\|_2$$""",
        "highlights": [
            "Synthesizes 300 realistic multi-line failure logs across 5 error archetypes: `Tool Schema Hallucination`, `Context Length Exceeded`, `API Timeout`, `Environment Permission Denied`, and `Infinite Loop`.",
            "Separates all 5 archetypes via unsupervised TF-IDF + $k$-Means (`Adjusted Rand Index = 1.000`, `Silhouette Score = 0.432`).",
            "Extracts centroid diagnostic keywords, medoid stack traces, and auto-generated **System Prompt Negative Constraints**, exporting both static PNG and interactive Plotly HTML scatter plots.",
        ],
    },
]


def main() -> None:
    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    for spec in CHAPTER_SPECS:
        slug = spec["slug"]
        ch_dir = CHAPTERS_DIR / slug
        ch_dir.mkdir(parents=True, exist_ok=True)

        # Copy executed notebook and standalone script into the chapter folder
        shutil.copy2(ROOT / f"{slug}.ipynb", ch_dir / f"{slug}.ipynb")
        shutil.copy2(ROOT / "scripts" / f"{slug}.py", ch_dir / f"{slug}.py")

        bullets = "\n".join([f"- {h}" for h in spec["highlights"]])
        readme_md = f"""# {spec['title']}

{spec['summary']}

---

## 📐 Mathematical Formulation

{spec['math']}

---

## ✨ Key Implementation Highlights

{bullets}

---

## 📊 Generated Visualization

![{spec['title']}](../../figures/{spec['figure']})

---

## 🚀 How to Run This Chapter

### 1. Interactive Jupyter Notebook
Open [`{slug}.ipynb`](./{slug}.ipynb) (pre-executed with all outputs and plots embedded) or launch JupyterLab from the repository root:
```bash
uv run jupyter lab chapters/{slug}/{slug}.ipynb
```

### 2. Standalone Python Script
Run the standalone script from the repository root:
```bash
uv run python chapters/{slug}/{slug}.py
```

### 3. Reusable Package Module
Import directly from [`{spec['module']}`](../../{spec['module']}):
```python
import agent_stats
```
"""
        (ch_dir / "README.md").write_text(readme_md, encoding="utf-8")
        print(f"Generated chapters/{slug}/README.md (+ notebook & script)")


if __name__ == "__main__":
    main()
