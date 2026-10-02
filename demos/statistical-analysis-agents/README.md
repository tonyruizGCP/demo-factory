# 📊 Statistical Analysis for AI Agent Evaluations (8-Chapter Interactive Series)

A comprehensive, hands-on curriculum and production-grade Python toolkit for **statistically rigorous evaluation, experimental design, and automated optimization of AI Agents**—designed for **both everyday intuitive understanding (layman metaphors & visual guides) and rigorous mathematical execution**.

Every chapter combines:
1. **🧠 Layman's Guide & Real-World Metaphors**: Plain-English explanations, intuitive analogies, and a **Jargon Buster** glossary translating statistical symbols into everyday engineering concepts.
2. **🎨 Visual Concept Illustrations (Generated with Nano Banana)**: Custom educational infographics (`figures/concepts/ch01_concept.jpg` – `ch08_concept.jpg`) illustrating the core intuition of each chapter.
3. **📐 Mathematical Derivations**: Exact combinatorics, frequentist power equations, response-surface calculus, and Bayesian conjugate/hierarchical posteriors.
4. **🔬 Synthetic Data & Simulation Engines**: Realistic multi-seed agent trajectory simulators (`agent_stats/`).
5. **📈 High-Resolution Statistical Plots**: Pre-rendered publication-grade charts (`figures/*.png`) and interactive Plotly HTML dashboards with panel-by-panel reading guides.
6. **📚 Curated Deeper Reading & References**: Foundational papers, textbooks, and practitioner guides.

---

## 🏛️ End-to-End Statistical Evaluation Lifecycle

```text
  [Ch 1: Multi-Seed Reliability]        [Ch 2: Data Hygiene & Splitting]
   Unbiased Pass@k vs. Pass^k    --->    Jointly Stratified 60/40 Split
   (Capability vs. Consistency)          + HoldoutGate (Anti-Goodharting)
                                                        |
                                                        v
  [Ch 5: Bayesian Early Stopping]       [Ch 3: Paired Frequentist A/B]
   Beta-Binomial Conjugate Step  <---    McNemar's Test (Discordant Pairs)
   (~74% Compute/Token Savings)          & Wilcoxon Signed-Rank (9.5x Power)
                 |
                 v
  [Ch 6: Hierarchical Shrinkage]        [Ch 4 & Ch 7: Harness Optimization]
   Empirical Bayes Partial Pool  --->    2nd-Order OLS Response Surface (Ch 4)
   (Edge-Case False-Alarm Guard)         & Gaussian Process BO / EI-UCB (Ch 7)
                                                        |
                                                        v
                                        [Ch 8: Unsupervised Trace Mining]
                                         Sublinear TF-IDF + PCA + K-Means
                                         -> System Prompt Negative Constraints
```

---

## 📚 Chapter-by-Chapter Directory, Metaphors & Key Takeaways

Each chapter has its own dedicated folder under [`chapters/`](./chapters/) containing an in-depth, layman-friendly **`README.md`**, a pre-executed **Jupyter Notebook (`.ipynb`)**, and a **standalone Python script (`.py`)**:

| Chapter | Chapter Guide (`README.md`) | Layman Metaphor | Interactive Notebook | Key Statistical Takeaway |
| :--- | :--- | :--- | :--- | :--- |
| **Chapter 1** | [**The Stochasticity Trap (`Pass@k` vs. `Pass^k`)**](./chapters/01_stochasticity_trap/README.md) | 🏹 *The Blindfolded Dart Thrower vs. The Precision Archer* | [`01_stochasticity_trap.ipynb`](./01_stochasticity_trap.ipynb) | Single-run $\text{Pass}@1$ masks execution variance: a flaky prompt with **76% $\text{Pass}@1$** collapses to **26% $\text{Pass}^5$**, whereas a deterministic 74% prompt achieves **66% $\text{Pass}^5$**. |
| **Chapter 2** | [**Data Hygiene & Overfitting Prevention**](./chapters/02_data_hygiene_and_overfitting/README.md) | 📝 *Memorizing the Practice Exam Answer Key vs. Learning the Subject* | [`02_data_hygiene_and_overfitting.ipynb`](./02_data_hygiene_and_overfitting.ipynb) | Ungated prompt hill-climbing diverges at **Step 9** due to reward hacking (Opt climbs to **91%**, Holdout drops to **52%**); `HoldoutGate` preserves **75%+** generalization. |
| **Chapter 3** | [**Frequentist A/B Testing & Power Analysis**](./chapters/03_frequentist_ab_testing/README.md) | 👟 *Testing Running Shoes on the Exact Same Obstacle Course* | [`03_frequentist_ab_testing.ipynb`](./03_frequentist_ab_testing.ipynb) | Paired **McNemar's Test** cancels task-difficulty noise, detecting a $+5\%$ lift ($65\% \to 70\%$) at $80\%$ power in **~145 paired tasks** vs. **~1,375 tasks** for an unpaired $Z$-test (**9.5x fewer runs**). |
| **Chapter 4** | [**Multi-Knob Attribution & Multiple Regression**](./chapters/04_multi_knob_attribution/README.md) | ☕ *Tuning an Espresso Machine & Avoiding the Overthinking Cliff* | [`04_multi_knob_attribution.ipynb`](./04_multi_knob_attribution.ipynb) | 2nd-order polynomial OLS ($R^2 = 0.94$) across `thinking_budget`, `context_chunks`, and `tool_timeout` locates the stationary optimum (~2,690 tokens, 14.1 chunks) and quantifies overthinking decay. |
| **Chapter 5** | [**Bayesian Sequential Testing & Early Stopping**](./chapters/05_bayesian_sequential_testing/README.md) | 🍲 *The Restaurant Taste-Tester: Why Eat 500 Spoonfuls of Burnt Soup?* | [`05_bayesian_sequential_testing.ipynb`](./05_bayesian_sequential_testing.ipynb) | Conjugate $\text{Beta}(\alpha+s, \beta+n-s)$ updating with Early Accept ($P \ge 0.95$) and Early Abandon ($P \le 0.10$) saves **~74% total evaluation compute** across 110 variants vs. fixed $N=500$ sweeps. |
| **Chapter 6** | [**Hierarchical Bayesian Modeling for Edge Cases**](./chapters/06_hierarchical_bayesian_modeling/README.md) | ⚾ *Opening-Day Baseball Batting Averages: Borrowing Strength from the League* | [`06_hierarchical_bayesian_modeling.ipynb`](./06_hierarchical_bayesian_modeling.ipynb) | Empirical Bayes Beta-Binomial partial pooling shrinks `distributed_race_condition` ($N=3, S=0$) from **0.0% raw** to **56.8%**, cutting category estimation RMSE by **68%**. |
| **Chapter 7** | [**Bayesian Optimization with Gaussian Processes**](./chapters/07_bayesian_optimization/README.md) | 🧭 *Prospecting for Gold in the Fog with a Smart Uncertainty Radar* | [`07_bayesian_optimization.ipynb`](./07_bayesian_optimization.ipynb) | Gaussian Process Regression (`Matern(nu=2.5)`) with Expected Improvement (EI) & GP-UCB converges on the unknown global optimum within **25 trials**. |
| **Chapter 8** | [**Failure Trace Mining & Unsupervised Clustering**](./chapters/08_failure_trace_clustering/README.md) | 🗂️ *Sorting a Mountain of 300 Crash Receipts into 5 Diagnostic Folders* | [`08_failure_trace_clustering.ipynb`](./08_failure_trace_clustering.ipynb) | Sublinear TF-IDF + PCA + $k$-Means clusters 300 raw failure logs into 5 error archetypes ($\text{ARI} = 1.000$) and auto-generates System Prompt **Negative Constraints**. |

---

## 🔍 Visual Concept Gallery & Statistical Plots (Chapters 1–8)

### Chapter 1: The Stochasticity Trap ($\text{Pass}@k$ vs. $\text{Pass}^k$)
> 📖 **Full Layman Guide, Glossary & References**: [`chapters/01_stochasticity_trap/README.md`](./chapters/01_stochasticity_trap/README.md)
>
> **Layman Intuition**: `Pass@k` asks *"Did at least 1 arrow out of $k$ hit the target?"* (great when a unit-test verifier filters out failed attempts). `Pass^k` asks *"Did ALL $k$ arrows hit the bullseye without a single miss?"* (critical when your agent serves live customers with no undo button).

![Chapter 1 Concept Visual](./figures/concepts/ch01_concept.jpg)
![Chapter 1 Statistical Plot](./figures/ch01_pass_at_k_vs_pass_pow_k.png)

---

### Chapter 2: Data Hygiene & Overfitting Prevention (Goodhart's Law)
> 📖 **Full Layman Guide, Glossary & References**: [`chapters/02_data_hygiene_and_overfitting/README.md`](./chapters/02_data_hygiene_and_overfitting/README.md)
>
> **Layman Intuition**: Tweaking a prompt 30 times against the same open benchmark is like letting a student memorize the exact answer key to a practice test. A **Jointly Stratified Holdout Gate** acts as a locked vault exam that blocks brittle "cheat-sheet" prompt mutations before they reach production.

![Chapter 2 Concept Visual](./figures/concepts/ch02_concept.jpg)
![Chapter 2 Statistical Plot](./figures/ch02_goodharts_law_holdout_gate.png)

---

### Chapter 3: Frequentist A/B Testing & Power Analysis (McNemar's Paired Test)
> 📖 **Full Layman Guide, Glossary & References**: [`chapters/03_frequentist_ab_testing/README.md`](./chapters/03_frequentist_ab_testing/README.md)
>
> **Layman Intuition**: Comparing two agents on different random tasks is like testing running shoes on different mountains—terrain noise drowns out the signal. Running both agents on the **exact same tasks** (McNemar's Test) cancels out task difficulty and focuses only on **discordant wins vs. regressions**, cutting required sample sizes by **9.5x**.

![Chapter 3 Concept Visual](./figures/concepts/ch03_concept.jpg)
![Chapter 3 Statistical Plot](./figures/ch03_mcnemar_power_and_wilcoxon.png)

---

### Chapter 4: Multi-Knob Attribution & Multiple Regression (Response Surfaces)
> 📖 **Full Layman Guide, Glossary & References**: [`chapters/04_multi_knob_attribution/README.md`](./chapters/04_multi_knob_attribution/README.md)
>
> **Layman Intuition**: Tuning `thinking_budget`, `context_chunks`, and `tool_timeout` one at a time misses **synergy boosts** (more thinking tokens require more context chunks to reason over) and **the Overthinking Cliff** (where excessive thinking budget causes analysis paralysis).

![Chapter 4 Concept Visual](./figures/concepts/ch04_concept.jpg)
![Chapter 4 Statistical Plot](./figures/ch04_multi_knob_response_surface.png)

---

### Chapter 5: Bayesian Sequential Testing & Early Stopping
> 📖 **Full Layman Guide, Glossary & References**: [`chapters/05_bayesian_sequential_testing/README.md`](./chapters/05_bayesian_sequential_testing/README.md)
>
> **Layman Intuition**: You don't need to eat 500 spoonfuls of burnt soup to know it's terrible! By updating a Beta probability curve after every single task, `BetaBinomialEvaluator` abandons hopeless prompts around Trial 25 and accepts clear winners early—saving **~74% of evaluation compute**.

![Chapter 5 Concept Visual](./figures/concepts/ch05_concept.jpg)
![Chapter 5 Statistical Plot](./figures/ch05_bayesian_sequential_stopping.png)

---

### Chapter 6: Hierarchical Bayesian Modeling for Edge Cases (Partial Pooling)
> 📖 **Full Layman Guide, Glossary & References**: [`chapters/06_hierarchical_bayesian_modeling/README.md`](./chapters/06_hierarchical_bayesian_modeling/README.md)
>
> **Layman Intuition**: If a baseball player goes `0-for-3` on Opening Day, their true skill isn't `0.0%`. **Hierarchical Bayesian Shrinkage** acts like a smart magnetic spring that pulls tiny, noisy edge-case categories ($N=3$) toward the global benchmark average while leaving large categories ($N=150$) anchored to their own data.

![Chapter 6 Concept Visual](./figures/concepts/ch06_concept.jpg)
![Chapter 6 Statistical Plot](./figures/ch06_hierarchical_forest_plot.png)

---

### Chapter 7: Bayesian Optimization with Gaussian Processes
> 📖 **Full Layman Guide, Glossary & References**: [`chapters/07_bayesian_optimization/README.md`](./chapters/07_bayesian_optimization/README.md)
>
> **Layman Intuition**: When each full benchmark sweep is expensive, Grid Search wastes 90% of trials in barren regions. A **Gaussian Process Surrogate** maps both the predicted score and the "fog of uncertainty," while **Expected Improvement (EI)** acts as a radar beacon guiding the next trial to the global peak in just **25 evaluations**.

![Chapter 7 Concept Visual](./figures/concepts/ch07_concept.jpg)
![Chapter 7 Statistical Plot](./figures/ch07_bayesian_optimization_surfaces.png)

---

### Chapter 8: Failure Trace Mining & Unsupervised Clustering
> 📖 **Full Layman Guide, Glossary & References**: [`chapters/08_failure_trace_clustering/README.md`](./chapters/08_failure_trace_clustering/README.md)
>
> **Layman Intuition**: Instead of manually reading 300 messy crash logs after an overnight run, **Sublinear TF-IDF + PCA + $k$-Means** acts like a crystal prism that sorts stack traces into 5 root-cause constellations, selects the single most representative **Medoid** log per bug class, and writes targeted **System Prompt Guardrails**.

![Chapter 8 Concept Visual](./figures/concepts/ch08_concept.jpg)
![Chapter 8 Statistical Plot](./figures/ch08_failure_trace_clusters.png)

---

## 📚 Master Reading List & Reference Material

1. **Chen, M., Tworek, J., Jun, H., et al. (2021).** *Evaluating Large Language Models Trained on Code (HumanEval).* arXiv:2107.03374. [https://arxiv.org/abs/2107.03374](https://arxiv.org/abs/2107.03374) *(Chapter 1 — Unbiased $\text{Pass}@k$)*
2. **Yao, S., Shinn, N., Razavi, P., & Narasimhan, K. (2024).** *$\tau$-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains.* arXiv:2406.12045. [https://arxiv.org/abs/2406.12045](https://arxiv.org/abs/2406.12045) *(Chapter 1 — $\text{Pass}^k$ Consistency)*
3. **Dwork, C., Feldman, V., Hardt, M., Pitassi, T., Reingold, O., & Roth, A. (2015).** *The Reusable Holdout: Preserving Validity in Adaptive Data Analysis.* Science, 349(6248), 636–638. *(Chapter 2 — Holdout Verification Gates)*
4. **McNemar, Q. (1947) & Dietterich, T. G. (1998).** *Approximate Statistical Tests for Comparing Supervised Classification Learning Algorithms.* Neural Computation, 10(7), 1895–1923. *(Chapter 3 — Paired A/B Testing)*
5. **Box, G. E. P., & Wilson, K. B. (1951) & Cuadron, A., et al. (2025).** *The Danger of Overthinking: Examining the Reasoning-Action Dilemma in Agentic Tasks.* arXiv:2502.08235. *(Chapter 4 — Response Surfaces & Overthinking Decay)*
6. **Wald, A. (1945) & Scott, S. L. (2010).** *A modern Bayesian look at the multi-armed bandit.* Applied Stochastic Models in Business and Industry, 26(6), 639–658. *(Chapter 5 — Sequential Beta-Binomial Testing)*
7. **Efron, B., & Morris, C. (1977) & Gelman, A., et al. (2013).** *Stein's Paradox in Statistics* & *Bayesian Data Analysis (3rd ed.).* *(Chapter 6 — Hierarchical Shrinkage & Partial Pooling)*
8. **Snoek, J., Larochelle, H., & Adams, R. P. (2012).** *Practical Bayesian Optimization of Machine Learning Algorithms.* NeurIPS 2012. [https://arxiv.org/abs/1206.2944](https://arxiv.org/abs/1206.2944) *(Chapter 7 — Gaussian Processes & Expected Improvement)*
9. **Salton, G., & Buckley, C. (1988) & Cemri, M., et al. (2025).** *Why Do Multi-Agent LLM Systems Fail? (MAST Taxonomy).* arXiv:2503.13657. [https://arxiv.org/abs/2503.13657](https://arxiv.org/abs/2503.13657) *(Chapter 8 — Unsupervised Failure Trace Clustering)*

---

## 🚀 Quickstart & Installation

### Option A: Using `uv` (Recommended)
```bash
# Install all scientific Python & Jupyter dependencies into .venv
uv sync

# Run any individual chapter script
uv run python scripts/05_bayesian_sequential_testing.py

# Rebuild and execute all 8 Jupyter Notebooks from scratch
uv run python build_and_run_all.py

# Regenerate per-chapter READMEs and notebook layman guides
uv run python generate_chapter_readmes.py

# Launch JupyterLab interactively
uv run jupyter lab
```

### Option B: Using Standard `venv` + `pip`
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 scripts/01_stochasticity_trap.py
jupyter lab
```

---

## 🔐 Security & Credentials Note

All 8 chapters run 100% locally and deterministically using synthetic benchmark generators (`numpy`, `scipy`, `statsmodels`, `scikit-learn`). No cloud credentials or API keys are required. When adapting these statistical evaluators to live LLM endpoints, store credentials in a local `.env` file (excluded via `.gitignore`) or authenticate via `gcloud auth application-default login`—never commit secrets or API keys to version control.
