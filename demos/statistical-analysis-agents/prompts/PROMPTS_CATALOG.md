# Ready-to-Use AI Coding Agent Prompts: Statistical Analysis for Agent Evaluations

This catalog stores the 8 canonical prompts for building interactive, runnable Jupyter Notebooks (`.ipynb`) and standalone Python scripts exploring statistical evaluation, experimental design, and automated optimization of AI agents.

---

## Chapter 1: The Stochasticity Trap ($\text{Pass}@k$ vs. $\text{Pass}^k$)

```markdown
Build an interactive Jupyter Notebook (`01_stochasticity_trap.ipynb`) exploring agent evaluation stochasticity, Pass@k, and Pass^k.

REQUIREMENTS:
1. Mathematical Derivations: Explain the combinatorial math behind Pass@k (unbiased estimator) and Pass^k (consistency estimator).
2. Simulation Engine:
   - Create a class `AgentStochasticitySimulator` that simulates an agent with a true underlying success probability distribution across N tasks over k repeated seeds.
   - Include controllable parameters for baseline capability and execution noise (variance).
3. Metric Implementations:
   - Implement `calculate_pass_at_k(n, c, k)` and `calculate_pass_pow_k(n, c, k)` using `scipy.special.comb`.
4. Visualizations (Matplotlib/Seaborn):
   - Plot 1: Pass@k vs. Pass^k curves as k increases from 1 to 10 for different agent profiles (e.g., "Lucky Flaky Agent" vs. "Consistent Deterministic Agent").
   - Plot 2: Heatmap showing the "Consistency Delta" (Pass@1 - Pass^k) across varying noise levels.
5. Interactive Hands-on Exercise:
   - Add a scenario where the user evaluates two prompt variants. Show how relying on single-run Pass@1 causes picking the wrong prompt, whereas Pass^k correctly identifies the production-ready prompt.
```

---

## Chapter 2: Data Hygiene & Overfitting Prevention

```markdown
Build a runnable Python script and Jupyter Notebook (`02_data_hygiene_and_overfitting.ipynb`) demonstrating Goodhart's Law and holdout verification gates in agent prompt optimization.

REQUIREMENTS:
1. Synthetic Benchmark Generator:
   - Generate a dataset of 200 benchmark tasks tagged with difficulty tiers (Easy, Medium, Hard) and capability tags (`tool_selection`, `context_retrieval`, `code_execution`).
2. Data Splitter:
   - Implement stratified train/holdout splitting (`sklearn.model_selection.train_test_split`) preserving joint difficulty and capability distributions across Optimization (60%) and Holdout (40%) sets.
3. Automated Prompt Hill-Climbing Loop:
   - Simulate an iterative optimizer making 30 sequential prompt mutations.
   - Simulate "Reward Hacking": some mutations improve genuine capability, while others exploit specific task quirks in the Optimization set without improving real reasoning.
4. Visualizations:
   - Plot Optimization Set Pass Rate vs. Holdout Set Pass Rate across iteration steps, highlighting the divergence point where overfitting occurs.
5. Holdout Gate Implementation:
   - Build a `HoldoutGate` class that evaluates candidate prompts on unseen holdout data and automatically rejects overfit mutations.
```

---

## Chapter 3: Frequentist A/B Testing & Power Analysis

```markdown
Build an interactive Jupyter Notebook (`03_frequentist_ab_testing.ipynb`) implementing rigorous paired A/B testing and statistical power analysis for agent evaluations.

REQUIREMENTS:
1. Power Analysis Calculator:
   - Write a function `calculate_required_sample_size(p1, p2, alpha=0.05, power=0.80)` for binary pass/fail agent tasks.
2. Synthetic Experiment Generator:
   - Simulate baseline vs. candidate agent runs on identical task sets, outputting paired binary outcomes (2x2 contingency table of task-level passes/fails).
3. Statistical Tests:
   - Implement **McNemar's Test** with continuity correction for paired binary outcomes.
   - Implement **Wilcoxon Signed-Rank Test** for skewed continuous metrics (e.g., token usage or execution time).
   - Implement an independent 2-sample Z-test to show why ignoring paired task structure is mathematically inferior.
4. Monte Carlo Sample-Efficiency Comparison:
   - Run 1,000 Monte Carlo trials demonstrating that McNemar's paired test requires 5x–10x fewer samples to detect a 5% pass rate improvement compared to an unlinked two-sample test.
```

---

## Chapter 4: Multi-Knob Attribution & Multiple Regression

```markdown
Build a Jupyter Notebook (`04_multi_knob_attribution.ipynb`) using multiple linear regression and second-order response surfaces to analyze agent configuration knobs.

REQUIREMENTS:
1. Data Generation:
   - Generate synthetic benchmark results (0.0 to 1.0 pass rate) resulting from tuning 3 continuous harness parameters:
     * `thinking_budget` (100 to 4000 tokens)
     * `context_chunks` (1 to 20 chunks)
     * `tool_timeout` (5 to 60 seconds)
   - Embed realistic effects: linear gains, quadratic decay (diminishing returns/overthinking), and interaction terms between `thinking_budget` and `context_chunks`.
2. Modeling (`statsmodels`):
   - Fit a Multiple Linear Regression model with interaction and quadratic polynomial terms (`Formula` API).
   - Display full summary tables ($R^2$, adjusted $R^2$, $p$-values, $t$-statistics, confidence intervals).
3. Visualizations:
   - Render 3D surface plots and 2D contour maps using `plotly` or `matplotlib` showing the optimal parameter region.
4. Developer Interpretation Exercises:
   - Provide code that extracts and prints plain-English insights (e.g., "Increasing thinking budget beyond 2,500 tokens reduces efficiency by X% per 100 tokens").
```

---

## Chapter 5: Bayesian Sequential Testing & Early Stopping

```markdown
Build a production-grade Python package and interactive notebook (`05_bayesian_sequential_testing.ipynb`) for Beta-Binomial conjugate updating and sequential early stopping.

REQUIREMENTS:
1. Mathematical Engine:
   - Implement closed-form Beta posterior updating: $\text{Beta}(\alpha + s, \, \beta + n - s)$.
   - Calculate Posterior Probability of Superiority $P(\theta_{\text{candidate}} > \theta_{\text{baseline}} \mid D)$ via Monte Carlo sampling (`numpy`) and exact numerical quadrature (`scipy.stats`).
2. Sequential Evaluator (`BetaBinomialEvaluator`):
   - Configurable boundaries: Early Accept ($P \ge 0.95$), Early Abandon ($P \le 0.10$).
   - Method `step(candidate_pass, baseline_pass)` that updates distributions and returns `ACCEPT`, `ABANDON`, or `CONTINUE`.
3. Compute-Savings Benchmark:
   - Simulate evaluating 100 weak prompt variants and 10 strong prompt variants against a baseline.
   - Compare total evaluation trials required under fixed $N=500$ sweeps vs. Bayesian sequential stopping.
4. Visualizations:
   - Animate or plot posterior distribution shifts step-by-step as task results arrive.
   - Plot a bar chart illustrating percentage compute/token savings (target: 40%–70% savings).
```

---

## Chapter 6: Hierarchical Bayesian Modeling for Edge Cases

```markdown
Build a Jupyter Notebook (`06_hierarchical_bayesian_modeling.ipynb`) demonstrating partial pooling and shrinkage across sparse agent failure categories.

REQUIREMENTS:
1. Synthetic Low-Data Problem Setup:
   - Create 8 task categories with uneven sample sizes ($N_j$ ranging from 3 to 150 tasks).
   - Include sparse categories like `distributed_race_condition` ($N=3$, $S=0$) and `memory_leak` ($N=4$, $S=1$).
2. Implement Three Estimators:
   - **No Pooling**: Raw empirical pass rate ($S_j / N_j$).
   - **Complete Pooling**: Ignoring categories, treating all tasks as one global average.
   - **Partial Pooling (Hierarchical Model)**: Use empirical Bayes or `PyMC` / `numpy` shrinkage formulas to pull category estimates toward the hyperprior mean.
3. Visualizations:
   - Create a forest plot comparing raw empirical pass rates vs. hierarchically shrunk estimates with 95% credible intervals.
4. Case Study Analysis:
   - Demonstrate why raw estimators cause developers to falsely declare catastrophic regressions on 3-sample edge cases, whereas hierarchical shrinkage prevents overreaction.
```

---

## Chapter 7: Bayesian Optimization with Gaussian Processes

```markdown
Build an interactive notebook (`07_bayesian_optimization.ipynb`) that uses Gaussian Process Regression to optimize continuous agent harness settings.

REQUIREMENTS:
1. Black-Box Agent Function:
   - Define a synthetic expensive black-box function `evaluate_harness_config(reasoning_tokens, context_limit)` that returns a noisy benchmark score with an unknown global optimum.
2. Gaussian Process & Acquisition Functions:
   - Use `scikit-learn.gaussian_process` (Matérn 5/2 kernel).
   - Implement **Expected Improvement (EI)** and **Upper Confidence Bound (GP-UCB)** acquisition functions.
3. Optimization Loop:
   - Build a loop that iteratively samples the most informative parameters, updates the GP surrogate model, and converges on the global maximum within 25 trials.
4. Visualizations:
   - For each iteration, render two side-by-side plots:
     1. GP predicted mean surface with uncertainty bounds.
     2. Acquisition function surface showing the next chosen sampling coordinate.
```

---

## Chapter 8: Failure Trace Mining & Unsupervised Clustering

```markdown
Build a Jupyter Notebook (`08_failure_trace_clustering.ipynb`) that parses raw agent execution logs, vectorizes error traces, and clusters failure modes for automated diagnosis.

REQUIREMENTS:
1. Log Synthesizer:
   - Generate 300 realistic agent failure logs containing stdout/stderr dumps, tool call payloads, and traceback strings across 5 underlying error archetypes (`Tool Schema Hallucination`, `Context Length Exceeded`, `API Timeout`, `Environment Permission Denied`, `Infinite Loop`).
2. Vectorization & Feature Extraction:
   - Process logs using TF-IDF (`sklearn.feature_extraction.text.TfidfVectorizer`) or dense sentence-transformer embeddings.
3. Clustering & Dimensionality Reduction:
   - Reduce dimensions using PCA or UMAP.
   - Cluster error traces using $k$-Means or HDBSCAN.
4. Auto-Diagnosis & Prompt Mutation Generation:
   - Extract top TF-IDF keywords / medoid log snippets for each cluster.
   - Write a function that converts cluster summaries into structured "Negative Constraints" ready to be injected into system prompt optimization loops.
5. Visualizations:
   - Render a 2D interactive scatter plot (`plotly`) of clustered failure traces labeled by cluster ID and key diagnostic phrases.
```
