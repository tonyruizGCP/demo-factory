# Chapter 2: Data Hygiene & Overfitting Prevention

Demonstrates Goodhart's Law ('when a measure becomes a target, it ceases to be a good measure') during iterative agent prompt hill-climbing, and implements a stratified `HoldoutGate` to block reward-hacking mutations.

---

## 📐 Mathematical Formulation

- **Joint Stratification Condition**:
  $$\mathbb{P}(D = d, C = c \mid \mathcal{D}_{\text{opt}}) = \mathbb{P}(D = d, C = c \mid \mathcal{D}_{\text{hold}})$$
  across Difficulty Tiers (`Easy`, `Medium`, `Hard`) $\times$ Capability Tags (`tool_selection`, `context_retrieval`, `code_execution`).
- **Holdout Gate Acceptance Rule**:
  $$\Delta \hat{R}_{\text{opt}} \ge \tau_{\text{opt}} \quad \wedge \quad \Delta \hat{R}_{\text{hold}} \ge 0 \quad \wedge \quad (\hat{R}_{\text{opt}} - \hat{R}_{\text{hold}}) \le \gamma_{\max}$$

---

## ✨ Key Implementation Highlights

- Generates 200 synthetic benchmark tasks across 9 difficulty $\times$ capability strata and splits them 60% Optimization ($n=120$) / 40% Holdout ($n=80$).
- Simulates 30 sequential prompt mutations mixing genuine capability improvements with benchmark-quirk reward hacking.
- Pinpoints the exact **Overfitting Divergence Step** where ungated optimization climbs to >90% on the Optimization set while collapsing to ~52% on unseen Holdout tasks.

---

## 📊 Generated Visualization

![Chapter 2: Data Hygiene & Overfitting Prevention](../../figures/ch02_goodharts_law_holdout_gate.png)

---

## 🚀 How to Run This Chapter

### 1. Interactive Jupyter Notebook
Open [`02_data_hygiene_and_overfitting.ipynb`](./02_data_hygiene_and_overfitting.ipynb) (pre-executed with all outputs and plots embedded) or launch JupyterLab from the repository root:
```bash
uv run jupyter lab chapters/02_data_hygiene_and_overfitting/02_data_hygiene_and_overfitting.ipynb
```

### 2. Standalone Python Script
Run the standalone script from the repository root:
```bash
uv run python chapters/02_data_hygiene_and_overfitting/02_data_hygiene_and_overfitting.py
```

### 3. Reusable Package Module
Import directly from [`agent_stats/ch02_hygiene_overfitting.py`](../../agent_stats/ch02_hygiene_overfitting.py):
```python
import agent_stats
```
