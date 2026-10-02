# Chapter 7: Bayesian Optimization with Gaussian Processes

Uses Gaussian Process Regression (`Matern(nu=2.5)` kernel) and acquisition functions (`Expected Improvement` and `GP-UCB`) to find the global optimum of an expensive black-box agent harness within 25 trials.

---

## 🎨 Visual Concept Overview (Generated with Nano Banana)

![Chapter 7: Bayesian Optimization with Gaussian Processes Concept Visual](../../figures/concepts/ch07_concept.jpg)

---

## 🧠 Layman's Guide: Prospecting for Gold in the Fog with a Smart Uncertainty Radar

Imagine searching for the deepest oil reservoir across a vast mountain range covered in thick fog, where **drilling a single test well costs \$10,000** (just like running a full 500-task agent benchmark suite costs hours of GPU/API time):

- **Grid Search (The Brute-Force Way)**: Drilling a well every 100 yards on a $10 \times 10$ grid requires **100 wells (\$1,000,000)**—and 90% of those wells are wasted in flat, barren desert!
- **Bayesian Optimization (The Smart Radar)**:
  1. **The Surrogate Map (Gaussian Process)**: You drill 5 initial random wells. Between those 5 pins, the Gaussian Process draws a smooth contour map of the likely terrain (**Predicted Mean $\mu$**) AND a "Fog Thickness Map" (**Uncertainty $\sigma$**) that is zero right where you drilled and thickens in unexplored regions.
  2. **The Acquisition Compass (`Expected Improvement`)**: Where should you drill Well #6? You want a spot that either has a **high predicted score** (*Exploitation: drilling near your best discovery so far*) OR **huge uncertainty** (*Exploration: checking a big foggy corner that might hide a giant peak*). The Acquisition Function combines both into a single glowing beacon pointing to the exact most informative coordinate to test next!

Within just **25 trials** (instead of 100+ grid points), Bayesian Optimization locks onto the global peak.

---

## 🧗 Why This Matters for Agentic Hill-Climbing

> **Role in the Optimization Loop**: **Stage 7 — Escaping Local Optima via Sample-Efficient Global Search (`CANDIDATE_SEARCH` Engine)**

Standard greedy **Agentic Hill-Climbing** suffers from a classic fatal flaw: **getting trapped on a local hill (local optimum)**.

- **What Breaks Without It (Stuck on a Foothill)**: Suppose your agent harness has a local performance bump around `reasoning_tokens=1,200, context_limit=25k` (72% pass rate) and a much taller global peak at `reasoning_tokens=2,850, context_limit=85k` (86% pass rate), separated by a dip. A greedy local hill-climber that only takes small steps uphill climbs onto the 72% foothill, sees the score drop in every immediate direction, and stops forever—missing the 86% global peak!
- **How It Supercharges the Hill-Climber**:
  1. **Memory of Uncertainty ($\sigma(\mathbf{x})$)**: Unlike greedy hill-climbing (which only remembers the current best point), a **Gaussian Process (`Matern 5/2`) Surrogate** remembers *every* configuration tested so far and knows exactly which regions of the parameter space are still unexplored (high $\sigma$).
  2. **Automated Exploration-Exploitation Switching**: When the local hill flattens out, the **Expected Improvement (EI)** and **GP-UCB** acquisition functions automatically shift weight to the exploration term $\sigma(\mathbf{x})\phi(Z)$, launching a targeted probe across the valley to discover the true global peak within **25 evaluations**.

---

## 📖 Plain-English Terminology & Jargon Buster

| Term / Symbol | Plain-English Meaning |
| :--- | :--- |
| **Black-Box Function** | A system (like a full agent benchmark run) where you can plug in configuration numbers and observe the final pass-rate score, but you don't have a simple math formula for what happens inside. |
| **Gaussian Process (GP) Surrogate** | A flexible statistical model that fits a smooth curve through the points you've tested so far, while also calculating a confidence band (uncertainty $\sigma$) at every untested point. |
| **Matérn 5/2 Kernel** | The 'smoothness rule' used by the Gaussian Process. Unlike overly smooth curves, Matérn 5/2 allows realistic bumps and sharp ridges common in ML hyperparameters. |
| **Exploration vs. Exploitation** | The fundamental dilemma: should you test right next to your current best setting (**Exploit**) or test a totally unknown region where uncertainty is high (**Explore**)? |
| **Acquisition Function (`Expected Improvement` / `GP-UCB`)** | A cheap formula that scores every possible untested setting based on both its predicted mean $\mu(x)$ and its uncertainty $\sigma(x)$, picking the highest scorer as the next trial. |

---

## 📐 Mathematical Formulation (Step-by-Step)

- **Matérn $\nu = 5/2$ Covariance Kernel**:
  Determines how strongly two parameter configurations $\mathbf{x}$ and $\mathbf{x}'$ correlate as a function of scaled distance $r = \|\mathbf{x} - \mathbf{x}'\|_{\mathbf{\ell}}$:
  $$k_{5/2}(r) = \sigma_f^2 \left(1 + \sqrt{5}r + \frac{5}{3}r^2\right)\exp(-\sqrt{5}r)$$
- **Expected Improvement (EI) & Upper Confidence Bound (GP-UCB)**:
  Given current best observed score $y^+$, predicted mean $\mu(\mathbf{x})$, and uncertainty $\sigma(\mathbf{x})$ (with $Z = \frac{\mu(\mathbf{x}) - y^+ - \xi}{\sigma(\mathbf{x})}$):
  $$\text{EI}(\mathbf{x}) = \underbrace{(\mu(\mathbf{x}) - y^+ - \xi)\Phi(Z)}_{\text{Exploitation Term}} + \underbrace{\sigma(\mathbf{x})\phi(Z)}_{\text{Exploration Term}}, \qquad \text{UCB}(\mathbf{x}) = \mu(\mathbf{x}) + \kappa\sigma(\mathbf{x})$$

---

## ✨ Key Implementation & Simulation Highlights

- Models the multimodal black-box objective `evaluate_harness_config(reasoning_tokens, context_limit)` using `scikit-learn` `GaussianProcessRegressor`.
- Iteratively balances exploration (high posterior uncertainty $\sigma$) and exploitation (high posterior mean $\mu$) over 25 evaluations.
- Renders side-by-side GP Posterior Mean/Uncertainty contours and Expected Improvement acquisition surfaces at Trials 5, 12, and 25.

---

## 📊 Generated Statistical Visualization & How to Read It

![Chapter 7: Bayesian Optimization with Gaussian Processes Statistical Plot](../../figures/ch07_bayesian_optimization_surfaces.png)

### 🔍 How to Read This Chart (Panel-by-Panel)
- **Top Row (Gaussian Process Predicted Mean & Uncertainty)**: Read from left to right (`Trial 5` $\to$ `Trial 12` $\to$ `Trial 25`). At `Trial 5`, with only 5 white dots tested, the GP map is blurry and rough. By `Trial 12` and `Trial 25`, the optimizer has concentrated sample dots around the true peak (gold star at ~2,850 tokens, ~85 KB context), bringing the discovered best (cyan star) right onto the global maximum!
- **Bottom Row (Expected Improvement Acquisition Surface)**: Bright yellow regions show where the optimizer wants to sample next (marked by the red triangle $\blacktriangle$). Notice how as regions are explored, their Expected Improvement drops to dark purple, pushing the red triangle to remaining promising zones until convergence.

---

## 🚀 How to Run This Chapter

### 1. Interactive Jupyter Notebook
Open [`07_bayesian_optimization.ipynb`](./07_bayesian_optimization.ipynb) (pre-executed with all outputs, layman guides, and plots embedded) or launch JupyterLab from the repository root:
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

---

## 📚 Resources & Reference Material for Deeper Reading

1. **Snoek, J., Larochelle, H., & Adams, R. P. (2012).** *Practical Bayesian Optimization of Machine Learning Algorithms.* NeurIPS 2012. [https://arxiv.org/abs/1206.2944](https://arxiv.org/abs/1206.2944) — The landmark paper that popularized GP Bayesian Optimization with Matérn 5/2 kernels for ML hyperparameter tuning.
2. **Shahriari, B., Swersky, K., Wang, Z., Adams, R. P., & de Freitas, N. (2016).** *Taking the Human Out of the Loop: A Review of Bayesian Optimization.* Proceedings of the IEEE, 104(1), 148–175.
3. **Rasmussen, C. E., & Williams, C. K. I. (2006).** *Gaussian Processes for Machine Learning.* MIT Press. [http://www.gaussianprocess.org/gpml/](http://www.gaussianprocess.org/gpml/)
4. **Garnett, R. (2023).** *Bayesian Optimization.* Cambridge University Press. [https://bayesoptbook.com/](https://bayesoptbook.com/)
