# Chapter 2: Data Hygiene & Overfitting Prevention

Demonstrates Goodhart's Law ('when a measure becomes a target, it ceases to be a good measure') during iterative agent prompt hill-climbing, and implements a stratified `HoldoutGate` to block reward-hacking mutations.

---

## 🎨 Visual Concept Overview (Generated with Nano Banana)

![Chapter 2: Data Hygiene & Overfitting Prevention Concept Visual](../../figures/concepts/ch02_concept.jpg)

---

## 🧠 Layman's Guide: Memorizing the Practice Exam Answer Key vs. Learning the Subject

Suppose a teacher wants to know if students truly understand algebra. They create a 100-question test, hand the exact questions and answer key to the class on Monday, and let students practice on that exact sheet 30 times before Friday.

By Friday, a student might score **95%** simply by memorizing rules like *"Whenever a question mentions a red train, the answer is 42"*—without knowing how to solve a single equation! The moment you give that student a **fresh exam locked in a vault** with slightly different word problems, their score crashes back to **52%**.

### Why This Matters for AI Agents
In modern AI engineering, developers (and automated prompt optimizers like DSPy or OPRO) tweak a system prompt 20 to 50 times in a row against a benchmark dataset:
- **Goodhart's Law**: *"When a measure becomes a target, it ceases to be a good measure."* If you look at the errors on your 120 test tasks and add hyper-specific rules to your prompt (*"If the user asks about SQL table `orders_v2`, always join on `cust_id`"*), your score on those 120 tasks goes up, but your prompt gets bloated, brittle, and worse at everything else.
- **The Stratified Holdout Gate**: By splitting your benchmark into an **Optimization Set (60%)** that you can inspect freely and a **Locked Holdout Vault (40%)** with the exact same mix of task difficulties and skills, an automated gate can immediately reject "cheat-sheet" prompt edits that don't generalize.

---

## 📖 Plain-English Terminology & Jargon Buster

| Term / Symbol | Plain-English Meaning |
| :--- | :--- |
| **Goodhart's Law** | The principle that once you relentlessly optimize directly for a specific test score, that score stops reflecting real-world quality. |
| **Overfitting / Reward Hacking** | Adding brittle, overly specific rules or shortcuts to a prompt that boost scores on known test cases while hurting performance on new tasks. |
| **Optimization Set ($\mathcal{D}_{\text{opt}}$)** | The 'open-book practice exam' (60% of tasks) where developers and prompt optimizers are allowed to inspect failures and iterate. |
| **Holdout Set ($\mathcal{D}_{\text{hold}}$)** | The 'locked vault exam' (40% of tasks) used strictly as a pass/fail gate to verify that prompt improvements actually generalize. |
| **Joint Stratification** | Splitting tasks so both the Practice Set and the Holdout Set have the exact same percentage of Easy/Medium/Hard tasks and tool categories. |
| **Generalization Gap** | The difference between your score on the Optimization Set and your score on the Holdout Set ($\hat{R}_{\text{opt}} - \hat{R}_{\text{hold}}$). A widening gap is the smoking gun of overfitting. |

---

## 📐 Mathematical Formulation (Step-by-Step)

- **Joint Stratification Condition**:
  Ensures every combination of Difficulty Tier $D \in \{\text{Easy}, \text{Medium}, \text{Hard}\}$ and Capability Tag $C \in \{\text{tool\_selection}, \text{context\_retrieval}, \text{code\_execution}\}$ is identically represented in both splits:
  $$\mathbb{P}(D = d, C = c \mid \mathcal{D}_{\text{opt}}) = \mathbb{P}(D = d, C = c \mid \mathcal{D}_{\text{hold}})$$
- **Holdout Gate Acceptance Rule**:
  A candidate prompt mutation is accepted if and only if it improves the optimization set by at least $\tau_{\text{opt}}$, does not regress on the holdout set, and keeps the generalization gap below $\gamma_{\max}$:
  $$\Delta \hat{R}_{\text{opt}} \ge \tau_{\text{opt}} \quad \wedge \quad \Delta \hat{R}_{\text{hold}} \ge 0 \quad \wedge \quad (\hat{R}_{\text{opt}} - \hat{R}_{\text{hold}}) \le \gamma_{\max}$$

---

## ✨ Key Implementation & Simulation Highlights

- Generates 200 synthetic benchmark tasks across 9 difficulty $\times$ capability strata and splits them 60% Optimization ($n=120$) / 40% Holdout ($n=80$).
- Simulates 30 sequential prompt mutations mixing genuine capability improvements with benchmark-quirk reward hacking.
- Pinpoints the exact **Overfitting Divergence Step** where ungated optimization climbs to >90% on the Optimization set while collapsing to ~52% on unseen Holdout tasks.

---

## 📊 Generated Statistical Visualization & How to Read It

![Chapter 2: Data Hygiene & Overfitting Prevention Statistical Plot](../../figures/ch02_goodharts_law_holdout_gate.png)

### 🔍 How to Read This Chart (Panel-by-Panel)
- **Left Panel (Joint Stratification Balance)**: Shows that all 9 combinations of `Difficulty × Capability` have the exact same 60% / 40% proportion in both sets—so no difference in score can be blamed on the Holdout Set being "accidentally harder."
- **Right Panel (Prompt Hill-Climbing Trajectory)**:
  - Look at the **Ungated Curves (dashed)**: The blue optimization score keeps climbing past 90%, tricking the developer into thinking they are making progress, while the red holdout score peaks around Step 9 and crashes down to ~52% (the red shaded zone is pure overfitting!).
  - Look at the **Holdout-Gated Curve (solid green)**: Whenever a mutation tries to "cheat" the benchmark, the `HoldoutGate` rejects it, preserving a clean, high ~75% true generalization score.

---

## 🚀 How to Run This Chapter

### 1. Interactive Jupyter Notebook
Open [`02_data_hygiene_and_overfitting.ipynb`](./02_data_hygiene_and_overfitting.ipynb) (pre-executed with all outputs, layman guides, and plots embedded) or launch JupyterLab from the repository root:
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

---

## 📚 Resources & Reference Material for Deeper Reading

1. **Goodhart, C. A. E. (1975).** *Problems of Monetary Management: The U.K. Experience.* Papers in Monetary Economics, Reserve Bank of Australia.
2. **Strathern, M. (1997).** *'Improving ratings': audit in the British University system.* European Review, 5(3), 305–321.
3. **Dwork, C., Feldman, V., Hardt, M., Pitassi, T., Reingold, O., & Roth, A. (2015).** *The Reusable Holdout: Preserving Validity in Adaptive Data Analysis.* Science, 349(6248), 636–638. [https://doi.org/10.1126/science.aaa9375](https://doi.org/10.1126/science.aaa9375)
4. **Zhang, H., et al. (2024).** *A Careful Examination of Large Language Model Performance on Grade School Arithmetic (GSM1k).* arXiv:2405.00332. [https://arxiv.org/abs/2405.00332](https://arxiv.org/abs/2405.00332) — Demonstrates benchmark overfitting across LLM leaderboards.
