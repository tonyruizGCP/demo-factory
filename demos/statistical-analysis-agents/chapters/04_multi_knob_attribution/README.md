# Chapter 4: Multi-Knob Attribution & Multiple Regression

Fits a second-order polynomial response surface (`statsmodels` Formula OLS) across three continuous agent harness knobs (`thinking_budget`, `context_chunks`, `tool_timeout`) to isolate linear gains, quadratic overthinking decay, and parameter interaction synergies.

---

## 📐 Mathematical Formulation

- **Second-Order Response Surface Model**:
  $$\text{PassRate} = \beta_0 + \beta_T T + \beta_{T^2} T^2 + \beta_C C + \beta_{C^2} C^2 + \beta_{TC}(T \cdot C) + \beta_S S + \epsilon$$
- **Stationary Optimum $(T^*, C^*)$**:
  $$\begin{bmatrix} 2\beta_{T^2} & \beta_{TC} \\ \beta_{TC} & 2\beta_{C^2} \end{bmatrix} \begin{bmatrix} T^* \\ C^* \end{bmatrix} = \begin{bmatrix} -\beta_T \\ -\beta_C \end{bmatrix}$$

---

## ✨ Key Implementation Highlights

- Fits a full quadratic + interaction OLS regression ($R^2 = 0.94$) with $t$-statistics, $p$-values, and confidence intervals.
- Renders 3D surface plots and 2D iso-performance contour maps pinpointing the stationary optimum (~2,690 thinking tokens, ~14.1 context chunks).
- Automatically extracts plain-English developer insights quantifying the marginal efficiency loss per 100 tokens past the overthinking threshold.

---

## 📊 Generated Visualization

![Chapter 4: Multi-Knob Attribution & Multiple Regression](../../figures/ch04_multi_knob_response_surface.png)

---

## 🚀 How to Run This Chapter

### 1. Interactive Jupyter Notebook
Open [`04_multi_knob_attribution.ipynb`](./04_multi_knob_attribution.ipynb) (pre-executed with all outputs and plots embedded) or launch JupyterLab from the repository root:
```bash
uv run jupyter lab chapters/04_multi_knob_attribution/04_multi_knob_attribution.ipynb
```

### 2. Standalone Python Script
Run the standalone script from the repository root:
```bash
uv run python chapters/04_multi_knob_attribution/04_multi_knob_attribution.py
```

### 3. Reusable Package Module
Import directly from [`agent_stats/ch04_multi_knob_regression.py`](../../agent_stats/ch04_multi_knob_regression.py):
```python
import agent_stats
```
