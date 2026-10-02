# Chapter 7: Bayesian Optimization with Gaussian Processes

Uses Gaussian Process Regression (`Matern(nu=2.5)` kernel) and acquisition functions (`Expected Improvement` and `GP-UCB`) to find the global optimum of an expensive black-box agent harness within 25 trials.

---

## 📐 Mathematical Formulation

- **Matérn $5/2$ Covariance Kernel**:
  $$k_{5/2}(r) = \sigma_f^2 \left(1 + \sqrt{5}r + \frac{5}{3}r^2\right)\exp(-\sqrt{5}r)$$
- **Expected Improvement (EI) & GP-UCB**:
  $$\text{EI}(\mathbf{x}) = (\mu(\mathbf{x}) - y^+ - \xi)\Phi(Z) + \sigma(\mathbf{x})\phi(Z), \qquad \text{UCB}(\mathbf{x}) = \mu(\mathbf{x}) + \kappa\sigma(\mathbf{x})$$

---

## ✨ Key Implementation Highlights

- Models the multimodal black-box objective `evaluate_harness_config(reasoning_tokens, context_limit)` using `scikit-learn` `GaussianProcessRegressor`.
- Iteratively balances exploration (high posterior uncertainty $\sigma$) and exploitation (high posterior mean $\mu$) over 25 evaluations.
- Renders side-by-side GP Posterior Mean/Uncertainty contours and Expected Improvement acquisition surfaces at Trials 5, 12, and 25.

---

## 📊 Generated Visualization

![Chapter 7: Bayesian Optimization with Gaussian Processes](../../figures/ch07_bayesian_optimization_surfaces.png)

---

## 🚀 How to Run This Chapter

### 1. Interactive Jupyter Notebook
Open [`07_bayesian_optimization.ipynb`](./07_bayesian_optimization.ipynb) (pre-executed with all outputs and plots embedded) or launch JupyterLab from the repository root:
```bash
uv run jupyter lab chapters/07_bayesian_optimization/07_bayesian_optimization.ipynb
```

### 2. Standalone Python Script
Run the standalone script from the repository root:
```bash
uv run python chapters/07_bayesian_optimization/07_bayesian_optimization.py
```

### 3. Reusable Package Module
Import directly from [`agent_stats/ch07_bayesian_optimization.py`](../../agent_stats/ch07_bayesian_optimization.py):
```python
import agent_stats
```
