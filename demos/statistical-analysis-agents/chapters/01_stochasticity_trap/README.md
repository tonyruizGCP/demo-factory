# Chapter 1: The Stochasticity Trap (`Pass@k` vs. `Pass^k`)

Explores execution variance across repeated evaluation seeds and contrasts the optimistic capability metric (`Pass@k`, at least 1 of `k` trials succeeds) against the production consistency metric (`Pass^k`, all `k` trials succeed).

---

## 📐 Mathematical Formulation

- **Unbiased $\text{Pass}@k$ Estimator (Chen et al., 2021)**:
  $$\widehat{\text{Pass}@k} = 1 - \frac{\binom{n - c}{k}}{\binom{n}{k}}$$
- **Unbiased $\text{Pass}^k$ Consistency Estimator ($\tau$-bench, Yao et al., 2024)**:
  $$\widehat{\text{Pass}^k} = \frac{\binom{c}{k}}{\binom{n}{k}}, \qquad \widehat{\text{Pass}^k}_{\text{plugin}} = \left(\frac{c}{n}\right)^k$$

---

## ✨ Key Implementation Highlights

- `AgentStochasticitySimulator`: Simulates $N=200$ tasks over $n=20$ seeds with controllable baseline capability and execution noise.
- **Visualizations**: $\text{Pass}@k$ vs. $\text{Pass}^k$ curves ($k=1\dots 10$) and a $7 \times 7$ **Consistency Delta Heatmap** ($\text{Pass}@1 - \text{Pass}^5$).
- **Hands-on Prompt Audit**: Demonstrates how a single-seed $\text{Pass}@1$ run mistakenly selects a flaky prompt (76% $\text{Pass}@1$, **26% $\text{Pass}^5$**) over a production-grade deterministic prompt (74% $\text{Pass}@1$, **66% $\text{Pass}^5$**).

---

## 📊 Generated Visualization

![Chapter 1: The Stochasticity Trap (`Pass@k` vs. `Pass^k`)](../../figures/ch01_pass_at_k_vs_pass_pow_k.png)

---

## 🚀 How to Run This Chapter

### 1. Interactive Jupyter Notebook
Open [`01_stochasticity_trap.ipynb`](./01_stochasticity_trap.ipynb) (pre-executed with all outputs and plots embedded) or launch JupyterLab from the repository root:
```bash
uv run jupyter lab chapters/01_stochasticity_trap/01_stochasticity_trap.ipynb
```

### 2. Standalone Python Script
Run the standalone script from the repository root:
```bash
uv run python chapters/01_stochasticity_trap/01_stochasticity_trap.py
```

### 3. Reusable Package Module
Import directly from [`agent_stats/ch01_stochasticity.py`](../../agent_stats/ch01_stochasticity.py):
```python
import agent_stats
```
