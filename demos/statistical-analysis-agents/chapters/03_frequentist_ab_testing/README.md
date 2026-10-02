# Chapter 3: Frequentist A/B Testing & Power Analysis

Implements rigorous paired A/B testing (`McNemar's Test` for binary pass/fail outcomes and `Wilcoxon Signed-Rank Test` for skewed token/latency metrics) alongside statistical power analysis.

---

## 📐 Mathematical Formulation

- **McNemar's Paired Test with Edwards' Continuity Correction**:
  $$\chi^2_{\text{McNemar}} = \frac{(|b - c| - 1)^2}{b + c} \sim \chi^2_1$$
  where $b$ is the count of regressions (Baseline Pass, Candidate Fail) and $c$ is the count of newly solved tasks (Baseline Fail, Candidate Pass).
- **Paired Sample Size Reduction**: Conditioning on identical tasks cancels shared task-difficulty variance, shrinking discordant proportion $\psi = p_b + p_c$.

---

## ✨ Key Implementation Highlights

- `calculate_required_sample_size`: Computes required task counts for both unpaired 2-sample $Z$-tests and paired McNemar tests.
- **1,000-Trial Monte Carlo Power Benchmark**: Proves that detecting a $+5\%$ pass rate lift ($65\% \to 70\%$) at $80\%$ power requires **~145 paired tasks** with McNemar's test versus **~1,375 tasks per arm** with an unpaired $Z$-test (**9.5x sample reduction**).
- Applies the non-parametric **Wilcoxon Signed-Rank Test** to heavy-tailed log-normal token consumption distributions.

---

## 📊 Generated Visualization

![Chapter 3: Frequentist A/B Testing & Power Analysis](../../figures/ch03_mcnemar_power_and_wilcoxon.png)

---

## 🚀 How to Run This Chapter

### 1. Interactive Jupyter Notebook
Open [`03_frequentist_ab_testing.ipynb`](./03_frequentist_ab_testing.ipynb) (pre-executed with all outputs and plots embedded) or launch JupyterLab from the repository root:
```bash
uv run jupyter lab chapters/03_frequentist_ab_testing/03_frequentist_ab_testing.ipynb
```

### 2. Standalone Python Script
Run the standalone script from the repository root:
```bash
uv run python chapters/03_frequentist_ab_testing/03_frequentist_ab_testing.py
```

### 3. Reusable Package Module
Import directly from [`agent_stats/ch03_frequentist_ab.py`](../../agent_stats/ch03_frequentist_ab.py):
```python
import agent_stats
```
