# Chapter 6: Hierarchical Bayesian Modeling for Edge Cases

Demonstrates Empirical Bayes partial pooling and shrinkage across 8 agent failure categories with uneven sample sizes ($N_j \in [3, 150]$), preventing false regression panic on sparse edge-case slices.

---

## 📐 Mathematical Formulation

- **Hierarchical Beta-Binomial Model**:
  $$\theta_j \sim \text{Beta}(\alpha_0, \beta_0), \qquad S_j \mid \theta_j \sim \text{Binomial}(N_j, \theta_j)$$
- **Posterior Shrinkage Estimator**:
  $$\mathbb{E}[\theta_j \mid S_j, N_j] = \underbrace{\left(\frac{\kappa}{\kappa + N_j}\right)}_{B_j} \mu_0 + (1 - B_j)\left(\frac{S_j}{N_j}\right), \qquad \kappa = \alpha_0 + \beta_0$$

---

## ✨ Key Implementation Highlights

- Compares **No Pooling** ($S_j/N_j$), **Complete Pooling** ($\sum S_j / \sum N_j$), and **Partial Pooling** (Empirical Bayes marginal likelihood maximization).
- Demonstrates how `distributed_race_condition` ($N=3, S=0$, raw $0.0\%$) and `memory_leak` ($N=4, S=1$, raw $25.0\%$) are shrunk toward the population hyperprior mean ($56.8\%$ and $59.9\%$).
- Reduces category pass-rate estimation RMSE against true latent capability by **68%** compared to raw unpooled proportions.

---

## 📊 Generated Visualization

![Chapter 6: Hierarchical Bayesian Modeling for Edge Cases](../../figures/ch06_hierarchical_forest_plot.png)

---

## 🚀 How to Run This Chapter

### 1. Interactive Jupyter Notebook
Open [`06_hierarchical_bayesian_modeling.ipynb`](./06_hierarchical_bayesian_modeling.ipynb) (pre-executed with all outputs and plots embedded) or launch JupyterLab from the repository root:
```bash
uv run jupyter lab chapters/06_hierarchical_bayesian_modeling/06_hierarchical_bayesian_modeling.ipynb
```

### 2. Standalone Python Script
Run the standalone script from the repository root:
```bash
uv run python chapters/06_hierarchical_bayesian_modeling/06_hierarchical_bayesian_modeling.py
```

### 3. Reusable Package Module
Import directly from [`agent_stats/ch06_hierarchical_bayes.py`](../../agent_stats/ch06_hierarchical_bayes.py):
```python
import agent_stats
```
