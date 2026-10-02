# Chapter 1: The Stochasticity Trap (`Pass@k` vs. `Pass^k`)

Explores execution variance across repeated evaluation seeds and contrasts the optimistic capability metric (`Pass@k`, at least 1 of `k` trials succeeds) against the production consistency metric (`Pass^k`, all `k` trials succeed).

---

## 🎨 Visual Concept Overview (Generated with Nano Banana)

![Chapter 1: The Stochasticity Trap (`Pass@k` vs. `Pass^k`) Concept Visual](../../figures/concepts/ch01_concept.jpg)

---

## 🧠 Layman's Guide: The Blindfolded Dart Thrower vs. The Precision Archer

Imagine you are hiring an archer to protect a castle, and you give two candidates **5 arrows** each:

- **Candidate A (The Lucky Gambler — Measured by `Pass@k`)**: Throws 5 arrows wildly while spinning around. Four arrows fly into the stands, and **one lucky arrow hits the bullseye**. If your grading rule is *"Did at least one arrow out of 5 hit the target?"* (`Pass@5`), Candidate A gets a **100% score!**
- **Candidate B (The Precision Master — Measured by `Pass^k`)**: Calmly aims and lands **all 5 arrows** tightly inside the bullseye ring every single time. If your grading rule is *"Did ALL 5 arrows hit the target without a single miss?"* (`Pass^5`), only Candidate B passes.

### Why This Matters for AI Agents
Large Language Models (LLMs) are **stochastic** (non-deterministic)—even with the exact same prompt, slight sampling randomness or tool-timing differences can cause an agent to take a different reasoning path on each run:
- **`Pass@k` ("Try-Until-You-Win")** is great when you have an automated verifier—for example, an AI coding assistant that generates 5 candidate patches, runs your unit test suite on all 5, and only shows the user the 1 patch that passed.
- **`Pass^k` ("Zero-Defect Consistency")** is essential when an agent interacts directly with a live customer, executes a financial transaction, or modifies a database where **there is no undo button**. An agent that succeeds 75% of the time on 1 try (`Pass@1 = 75%`) will succeed 5 times in a row only $0.75^5 \approx 23.7\%$ of the time (`Pass^5 = 23.7%`)!

---

## 🧗 Why This Matters for Agentic Hill-Climbing

> **Role in the Optimization Loop**: **Stage 1 — Defining the Hill's Objective Function (Climbing True Altitude vs. Climbing Noise)**

In **Agentic Hill-Climbing**, an automated optimizer iteratively mutates your system prompt or tool definitions, scores the candidate against your benchmark, and keeps the mutation if the score goes up. **The metric you choose defines the "altitude" of the hill:**

- **What Breaks Without It (Climbing Execution Noise)**: If your hill-climber evaluates each prompt mutation using only a single seed (`Pass@1`) or optimizes `Pass@k` for a customer-facing agent, the optimizer will **mistake a lucky coin flip for a genuine improvement**. In our simulation, a chaotic/high-variance prompt gets lucky on a single run (`Pass@1 = 76%`) and tricks the hill-climber into replacing a rock-solid baseline (`Pass@1 = 74%`). Beneath the surface, that "upgrade" caused 5-run reliability (`Pass^5`) to crash from **66% down to 26%**!
- **How It Supercharges the Hill-Climber**:
  1. **Multi-Seed Evaluation ($n$ seeds per task)** smooths out trajectory variance so the hill-climber doesn't chase phantom 2% bumps caused by random LLM sampling.
  2. **Objective Alignment**: Using $\widehat{\text{Pass}@k}$ when hill-climbing a **verifier-backed coding harness** (where best-of-$k$ sampling is used at inference time) versus $\widehat{\text{Pass}^k}$ when hill-climbing an **autonomous transactional agent** guarantees that every accepted step up the hill improves real production reliability.

---

## 📖 Plain-English Terminology & Jargon Buster

| Term / Symbol | Plain-English Meaning |
| :--- | :--- |
| **Stochasticity** | Randomness in how an agent behaves from run to run, even when given the exact same task and prompt. |
| **Seed / Trial ($n$)** | One complete, independent attempt by the agent to solve a task from start to finish. |
| **`Pass@1`** | The basic success rate when you only run the agent once per task. |
| **`Pass@k` (Optimistic Capability)** | The probability that the agent solves the task **at least once** if given $k$ attempts. As $k$ grows, `Pass@k` goes **up**. |
| **`Pass^k` (Production Consistency)** | The probability that the agent solves the task **every single time** across $k$ back-to-back attempts. As $k$ grows, `Pass^k` goes **down**. |
| **Consistency Delta ($\text{Pass}@1 - \text{Pass}^k$)** | How much an agent's reliability drops when you require $k$ consecutive successes instead of just 1. A large delta means the agent is 'flaky'. |
| **Binomial Coefficient $\binom{n}{k}$** | Read as '$n$ choose $k$'—the total number of ways to pick $k$ runs out of $n$ recorded trials without caring about order. |

---

## 📐 Mathematical Formulation (Step-by-Step)

- **Unbiased $\text{Pass}@k$ Estimator (Chen et al., 2021)**:
  Instead of naively guessing from just $k$ trials, we run $n \ge k$ trials, count the $c$ successes, and compute the exact probability that a random subset of $k$ trials contains **at least one** success (1 minus the probability that all $k$ chosen trials are failures):
  $$\widehat{\text{Pass}@k} = 1 - \frac{\binom{n - c}{k}}{\binom{n}{k}}$$
- **Unbiased $\text{Pass}^k$ Consistency Estimator ($\tau$-bench, Yao et al., 2024)**:
  Computes the exact probability that all $k$ randomly selected trials come exclusively from the $c$ successful runs:
  $$\widehat{\text{Pass}^k} = \frac{\binom{c}{k}}{\binom{n}{k}}, \qquad \widehat{\text{Pass}^k}_{\text{plugin}} = \left(\frac{c}{n}\right)^k$$

---

## ✨ Key Implementation & Simulation Highlights

- `AgentStochasticitySimulator`: Simulates $N=200$ tasks over $n=20$ seeds with controllable baseline capability and execution noise.
- **Visualizations**: $\text{Pass}@k$ vs. $\text{Pass}^k$ curves ($k=1\dots 10$) and a $7 \times 7$ **Consistency Delta Heatmap** ($\text{Pass}@1 - \text{Pass}^5$).
- **Hands-on Prompt Audit**: Demonstrates how a single-seed $\text{Pass}@1$ run mistakenly selects a flaky prompt (76% $\text{Pass}@1$, **26% $\text{Pass}^5$**) over a production-grade deterministic prompt (74% $\text{Pass}@1$, **66% $\text{Pass}^5$**).

---

## 📊 Generated Statistical Visualization & How to Read It

![Chapter 1: The Stochasticity Trap (`Pass@k` vs. `Pass^k`) Statistical Plot](../../figures/ch01_pass_at_k_vs_pass_pow_k.png)

### 🔍 How to Read This Chart (Panel-by-Panel)
- **Left Panel (`Pass@k` vs. `Pass^k` Curves)**: Follow the solid lines (`Pass@k`) climbing toward 100% as $k$ increases from 1 to 10—even the "Lucky Flaky Agent" looks amazing if you give it 10 tries! Now look at the dashed lines (`Pass^k`): the Flaky Agent plummets toward 0%, while the "Consistent Deterministic Agent" stays resiliently high.
- **Right Panel (Consistency Delta Heatmap)**: The brighter/redder the square, the larger the gap between single-run appearance (`Pass@1`) and 5-run reliability (`Pass^5`). High execution noise creates a massive "reliability mirage" right around 60%–85% baseline capability.

---

## 🚀 How to Run This Chapter

### 1. Interactive Jupyter Notebook
Open [`01_stochasticity_trap.ipynb`](./01_stochasticity_trap.ipynb) (pre-executed with all outputs, layman guides, and plots embedded) or launch JupyterLab from the repository root:
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

---

## 📚 Resources & Reference Material for Deeper Reading

1. **Chen, M., Tworek, J., Jun, H., et al. (2021).** *Evaluating Large Language Models Trained on Code (HumanEval).* arXiv:2107.03374. [https://arxiv.org/abs/2107.03374](https://arxiv.org/abs/2107.03374) — Introduces the unbiased combinatorial $\text{Pass}@k$ estimator.
2. **Yao, S., Shinn, N., Razavi, P., & Narasimhan, K. (2024).** *$\tau$-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains.* arXiv:2406.12045. [https://arxiv.org/abs/2406.12045](https://arxiv.org/abs/2406.12045) — Introduces $\text{Pass}^k$ ($\text{pass}\text{^}k$) to measure enterprise agent reliability across repeated trials.
3. **Kapoor, S., Stroebl, B., Siegel, Z. S., Nadgir, N., & Narayanan, A. (2024).** *AI Agents That Matter.* arXiv:2407.01502. [https://arxiv.org/abs/2407.01502](https://arxiv.org/abs/2407.01502) — Discusses cost-controlled and variance-aware agent evaluation.
