r"""Generates comprehensive per-chapter README.md guides with layman explanations, metaphors,
Agentic Hill-Climbing relevance, terminology glossaries, Nano Banana concept visuals, chart walkthroughs,
and deeper reading references, and enriches the Jupyter notebooks with the same context.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
CHAPTERS_DIR = ROOT / "chapters"

CHAPTER_SPECS = [
    {
        "num": 1,
        "slug": "01_stochasticity_trap",
        "title": "Chapter 1: The Stochasticity Trap (`Pass@k` vs. `Pass^k`)",
        "module": "agent_stats/ch01_stochasticity.py",
        "figure": "ch01_pass_at_k_vs_pass_pow_k.png",
        "concept_img": "ch01_concept.jpg",
        "summary": (
            "Explores execution variance across repeated evaluation seeds and contrasts "
            "the optimistic capability metric (`Pass@k`, at least 1 of `k` trials succeeds) "
            "against the production consistency metric (`Pass^k`, all `k` trials succeed)."
        ),
        "metaphor_title": "The Blindfolded Dart Thrower vs. The Precision Archer",
        "layman_explanation": r"""Imagine you are hiring an archer to protect a castle, and you give two candidates **5 arrows** each:

- **Candidate A (The Lucky Gambler — Measured by `Pass@k`)**: Throws 5 arrows wildly while spinning around. Four arrows fly into the stands, and **one lucky arrow hits the bullseye**. If your grading rule is *"Did at least one arrow out of 5 hit the target?"* (`Pass@5`), Candidate A gets a **100% score!**
- **Candidate B (The Precision Master — Measured by `Pass^k`)**: Calmly aims and lands **all 5 arrows** tightly inside the bullseye ring every single time. If your grading rule is *"Did ALL 5 arrows hit the target without a single miss?"* (`Pass^5`), only Candidate B passes.

### Why This Matters for AI Agents
Large Language Models (LLMs) are **stochastic** (non-deterministic)—even with the exact same prompt, slight sampling randomness or tool-timing differences can cause an agent to take a different reasoning path on each run:
- **`Pass@k` ("Try-Until-You-Win")** is great when you have an automated verifier—for example, an AI coding assistant that generates 5 candidate patches, runs your unit test suite on all 5, and only shows the user the 1 patch that passed.
- **`Pass^k` ("Zero-Defect Consistency")** is essential when an agent interacts directly with a live customer, executes a financial transaction, or modifies a database where **there is no undo button**. An agent that succeeds 75% of the time on 1 try (`Pass@1 = 75%`) will succeed 5 times in a row only $0.75^5 \approx 23.7\%$ of the time (`Pass^5 = 23.7%`)!""",
        "hill_climbing_role": "Stage 1 — Defining the Hill's Objective Function (Climbing True Altitude vs. Climbing Noise)",
        "hill_climbing_explanation": r"""In **Agentic Hill-Climbing**, an automated optimizer iteratively mutates your system prompt or tool definitions, scores the candidate against your benchmark, and keeps the mutation if the score goes up. **The metric you choose defines the "altitude" of the hill:**

- **What Breaks Without It (Climbing Execution Noise)**: If your hill-climber evaluates each prompt mutation using only a single seed (`Pass@1`) or optimizes `Pass@k` for a customer-facing agent, the optimizer will **mistake a lucky coin flip for a genuine improvement**. In our simulation, a chaotic/high-variance prompt gets lucky on a single run (`Pass@1 = 76%`) and tricks the hill-climber into replacing a rock-solid baseline (`Pass@1 = 74%`). Beneath the surface, that "upgrade" caused 5-run reliability (`Pass^5`) to crash from **66% down to 26%**!
- **How It Supercharges the Hill-Climber**:
  1. **Multi-Seed Evaluation ($n$ seeds per task)** smooths out trajectory variance so the hill-climber doesn't chase phantom 2% bumps caused by random LLM sampling.
  2. **Objective Alignment**: Using $\widehat{\text{Pass}@k}$ when hill-climbing a **verifier-backed coding harness** (where best-of-$k$ sampling is used at inference time) versus $\widehat{\text{Pass}^k}$ when hill-climbing an **autonomous transactional agent** guarantees that every accepted step up the hill improves real production reliability.""",
        "glossary": [
            ("Stochasticity", "Randomness in how an agent behaves from run to run, even when given the exact same task and prompt."),
            ("Seed / Trial ($n$)", "One complete, independent attempt by the agent to solve a task from start to finish."),
            ("`Pass@1`", "The basic success rate when you only run the agent once per task."),
            ("`Pass@k` (Optimistic Capability)", "The probability that the agent solves the task **at least once** if given $k$ attempts. As $k$ grows, `Pass@k` goes **up**."),
            ("`Pass^k` (Production Consistency)", "The probability that the agent solves the task **every single time** across $k$ back-to-back attempts. As $k$ grows, `Pass^k` goes **down**."),
            ("Consistency Delta ($\\text{Pass}@1 - \\text{Pass}^k$)", "How much an agent's reliability drops when you require $k$ consecutive successes instead of just 1. A large delta means the agent is 'flaky'."),
            ("Binomial Coefficient $\\binom{n}{k}$", "Read as '$n$ choose $k$'—the total number of ways to pick $k$ runs out of $n$ recorded trials without caring about order."),
        ],
        "math": r"""- **Unbiased $\text{Pass}@k$ Estimator (Chen et al., 2021)**:
  Instead of naively guessing from just $k$ trials, we run $n \ge k$ trials, count the $c$ successes, and compute the exact probability that a random subset of $k$ trials contains **at least one** success (1 minus the probability that all $k$ chosen trials are failures):
  $$\widehat{\text{Pass}@k} = 1 - \frac{\binom{n - c}{k}}{\binom{n}{k}}$$
- **Unbiased $\text{Pass}^k$ Consistency Estimator ($\tau$-bench, Yao et al., 2024)**:
  Computes the exact probability that all $k$ randomly selected trials come exclusively from the $c$ successful runs:
  $$\widehat{\text{Pass}^k} = \frac{\binom{c}{k}}{\binom{n}{k}}, \qquad \widehat{\text{Pass}^k}_{\text{plugin}} = \left(\frac{c}{n}\right)^k$$""",
        "highlights": [
            "`AgentStochasticitySimulator`: Simulates $N=200$ tasks over $n=20$ seeds with controllable baseline capability and execution noise.",
            "**Visualizations**: $\\text{Pass}@k$ vs. $\\text{Pass}^k$ curves ($k=1\\dots 10$) and a $7 \\times 7$ **Consistency Delta Heatmap** ($\\text{Pass}@1 - \\text{Pass}^5$).",
            "**Hands-on Prompt Audit**: Demonstrates how a single-seed $\\text{Pass}@1$ run mistakenly selects a flaky prompt (76% $\\text{Pass}@1$, **26% $\\text{Pass}^5$**) over a production-grade deterministic prompt (74% $\\text{Pass}@1$, **66% $\\text{Pass}^5$**).",
        ],
        "chart_walkthrough": """- **Left Panel (`Pass@k` vs. `Pass^k` Curves)**: Follow the solid lines (`Pass@k`) climbing toward 100% as $k$ increases from 1 to 10—even the "Lucky Flaky Agent" looks amazing if you give it 10 tries! Now look at the dashed lines (`Pass^k`): the Flaky Agent plummets toward 0%, while the "Consistent Deterministic Agent" stays resiliently high.
- **Right Panel (Consistency Delta Heatmap)**: The brighter/redder the square, the larger the gap between single-run appearance (`Pass@1`) and 5-run reliability (`Pass^5`). High execution noise creates a massive "reliability mirage" right around 60%–85% baseline capability.""",
        "references": [
            "**Chen, M., Tworek, J., Jun, H., et al. (2021).** *Evaluating Large Language Models Trained on Code (HumanEval).* arXiv:2107.03374. [https://arxiv.org/abs/2107.03374](https://arxiv.org/abs/2107.03374) — Introduces the unbiased combinatorial $\\text{Pass}@k$ estimator.",
            "**Yao, S., Shinn, N., Razavi, P., & Narasimhan, K. (2024).** *$\\tau$-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains.* arXiv:2406.12045. [https://arxiv.org/abs/2406.12045](https://arxiv.org/abs/2406.12045) — Introduces $\\text{Pass}^k$ ($\\text{pass}\\text{^}k$) to measure enterprise agent reliability across repeated trials.",
            "**Kapoor, S., Stroebl, B., Siegel, Z. S., Nadgir, N., & Narayanan, A. (2024).** *AI Agents That Matter.* arXiv:2407.01502. [https://arxiv.org/abs/2407.01502](https://arxiv.org/abs/2407.01502) — Discusses cost-controlled and variance-aware agent evaluation.",
        ],
    },
    {
        "num": 2,
        "slug": "02_data_hygiene_and_overfitting",
        "title": "Chapter 2: Data Hygiene & Overfitting Prevention",
        "module": "agent_stats/ch02_hygiene_overfitting.py",
        "figure": "ch02_goodharts_law_holdout_gate.png",
        "concept_img": "ch02_concept.jpg",
        "summary": (
            "Demonstrates Goodhart's Law ('when a measure becomes a target, it ceases to be a good measure') "
            "during iterative agent prompt hill-climbing, and implements a stratified `HoldoutGate` to block "
            "reward-hacking mutations."
        ),
        "metaphor_title": "Memorizing the Practice Exam Answer Key vs. Learning the Subject",
        "layman_explanation": r"""Suppose a teacher wants to know if students truly understand algebra. They create a 100-question test, hand the exact questions and answer key to the class on Monday, and let students practice on that exact sheet 30 times before Friday.

By Friday, a student might score **95%** simply by memorizing rules like *"Whenever a question mentions a red train, the answer is 42"*—without knowing how to solve a single equation! The moment you give that student a **fresh exam locked in a vault** with slightly different word problems, their score crashes back to **52%**.

### Why This Matters for AI Agents
In modern AI engineering, developers (and automated prompt optimizers like DSPy or OPRO) tweak a system prompt 20 to 50 times in a row against a benchmark dataset:
- **Goodhart's Law**: *"When a measure becomes a target, it ceases to be a good measure."* If you look at the errors on your 120 test tasks and add hyper-specific rules to your prompt (*"If the user asks about SQL table `orders_v2`, always join on `cust_id`"*), your score on those 120 tasks goes up, but your prompt gets bloated, brittle, and worse at everything else.
- **The Stratified Holdout Gate**: By splitting your benchmark into an **Optimization Set (60%)** that you can inspect freely and a **Locked Holdout Vault (40%)** with the exact same mix of task difficulties and skills, an automated gate can immediately reject "cheat-sheet" prompt edits that don't generalize.""",
        "hill_climbing_role": "Stage 2 — The Anti-Goodharting Circuit Breaker (`HOLDOUT_GATE` & Stratified Partitioning)",
        "hill_climbing_explanation": r"""**Agentic Hill-Climbing** is, by definition, an iterative search loop that repeatedly queries a benchmark to improve a prompt or harness. Because LLM prompts have virtually infinite degrees of freedom (you can append arbitrary natural-language instructions), **hill-climbers are extraordinarily prone to overfitting**:

- **What Breaks Without It (Reward Hacking & Prompt Bloat)**: When an autonomous hill-climber (or human engineer) inspects failed trajectories on the training set and proposes 30 sequential prompt mutations, it quickly discovers **benchmark-specific shortcuts**—hardcoding edge-case answers, overfitting to specific test phrasing, or adding conflicting `CRITICAL: NEVER DO X` rules. In our simulation, after **Step 9**, ungated hill-climbing continues pushing the Optimization score above **91%**, while true performance on unseen tasks collapses to **52%**!
- **How It Supercharges the Hill-Climber**:
  1. **Jointly Stratified Splitting (`Difficulty × Capability`)** guarantees that rare, high-difficulty task slices (e.g., `Hard × code_execution`) are equally represented in both the Optimization climb set and the Holdout vault—preventing the hill-climber from gaming easy tasks.
  2. **Automated `HoldoutGate` Enforcement**: Before any candidate mutation is promoted as the new baseline in the hill-climbing state machine, it must pass the `HoldoutGate` ($\Delta \hat{R}_{\text{hold}} \ge 0$ and generalization gap $\hat{R}_{\text{opt}} - \hat{R}_{\text{hold}} \le \gamma_{\max}$). Overfit mutations are automatically rejected and rolled back, sustaining a clean **75%+ true generalization plateau**.""",
        "glossary": [
            ("Goodhart's Law", "The principle that once you relentlessly optimize directly for a specific test score, that score stops reflecting real-world quality."),
            ("Overfitting / Reward Hacking", "Adding brittle, overly specific rules or shortcuts to a prompt that boost scores on known test cases while hurting performance on new tasks."),
            ("Optimization Set ($\\mathcal{D}_{\\text{opt}}$)", "The 'open-book practice exam' (60% of tasks) where developers and prompt optimizers are allowed to inspect failures and iterate."),
            ("Holdout Set ($\\mathcal{D}_{\\text{hold}}$)", "The 'locked vault exam' (40% of tasks) used strictly as a pass/fail gate to verify that prompt improvements actually generalize."),
            ("Joint Stratification", "Splitting tasks so both the Practice Set and the Holdout Set have the exact same percentage of Easy/Medium/Hard tasks and tool categories."),
            ("Generalization Gap", "The difference between your score on the Optimization Set and your score on the Holdout Set ($\\hat{R}_{\\text{opt}} - \\hat{R}_{\\text{hold}}$). A widening gap is the smoking gun of overfitting."),
        ],
        "math": r"""- **Joint Stratification Condition**:
  Ensures every combination of Difficulty Tier $D \in \{\text{Easy}, \text{Medium}, \text{Hard}\}$ and Capability Tag $C \in \{\text{tool\_selection}, \text{context\_retrieval}, \text{code\_execution}\}$ is identically represented in both splits:
  $$\mathbb{P}(D = d, C = c \mid \mathcal{D}_{\text{opt}}) = \mathbb{P}(D = d, C = c \mid \mathcal{D}_{\text{hold}})$$
- **Holdout Gate Acceptance Rule**:
  A candidate prompt mutation is accepted if and only if it improves the optimization set by at least $\tau_{\text{opt}}$, does not regress on the holdout set, and keeps the generalization gap below $\gamma_{\max}$:
  $$\Delta \hat{R}_{\text{opt}} \ge \tau_{\text{opt}} \quad \wedge \quad \Delta \hat{R}_{\text{hold}} \ge 0 \quad \wedge \quad (\hat{R}_{\text{opt}} - \hat{R}_{\text{hold}}) \le \gamma_{\max}$$""",
        "highlights": [
            "Generates 200 synthetic benchmark tasks across 9 difficulty $\\times$ capability strata and splits them 60% Optimization ($n=120$) / 40% Holdout ($n=180$).",
            "Simulates 30 sequential prompt mutations mixing genuine capability improvements with benchmark-quirk reward hacking.",
            "Pinpoints the exact **Overfitting Divergence Step** where ungated optimization climbs to >90% on the Optimization set while collapsing to ~52% on unseen Holdout tasks.",
        ],
        "chart_walkthrough": """- **Left Panel (Joint Stratification Balance)**: Shows that all 9 combinations of `Difficulty × Capability` have the exact same 60% / 40% proportion in both sets—so no difference in score can be blamed on the Holdout Set being "accidentally harder."
- **Right Panel (Prompt Hill-Climbing Trajectory)**:
  - Look at the **Ungated Curves (dashed)**: The blue optimization score keeps climbing past 90%, tricking the developer into thinking they are making progress, while the red holdout score peaks around Step 9 and crashes down to ~52% (the red shaded zone is pure overfitting!).
  - Look at the **Holdout-Gated Curve (solid green)**: Whenever a mutation tries to "cheat" the benchmark, the `HoldoutGate` rejects it, preserving a clean, high ~75% true generalization score.""",
        "references": [
            "**Goodhart, C. A. E. (1975).** *Problems of Monetary Management: The U.K. Experience.* Papers in Monetary Economics, Reserve Bank of Australia.",
            "**Strathern, M. (1997).** *'Improving ratings': audit in the British University system.* European Review, 5(3), 305–321.",
            "**Dwork, C., Feldman, V., Hardt, M., Pitassi, T., Reingold, O., & Roth, A. (2015).** *The Reusable Holdout: Preserving Validity in Adaptive Data Analysis.* Science, 349(6248), 636–638. [https://doi.org/10.1126/science.aaa9375](https://doi.org/10.1126/science.aaa9375)",
            "**Zhang, H., et al. (2024).** *A Careful Examination of Large Language Model Performance on Grade School Arithmetic (GSM1k).* arXiv:2405.00332. [https://arxiv.org/abs/2405.00332](https://arxiv.org/abs/2405.00332) — Demonstrates benchmark overfitting across LLM leaderboards.",
        ],
    },
    {
        "num": 3,
        "slug": "03_frequentist_ab_testing",
        "title": "Chapter 3: Frequentist A/B Testing & Power Analysis",
        "module": "agent_stats/ch03_frequentist_ab.py",
        "figure": "ch03_mcnemar_power_and_wilcoxon.png",
        "concept_img": "ch03_concept.jpg",
        "summary": (
            "Implements rigorous paired A/B testing (`McNemar's Test` for binary pass/fail outcomes and "
            "`Wilcoxon Signed-Rank Test` for skewed token/latency metrics) alongside statistical power analysis."
        ),
        "metaphor_title": "Testing Running Shoes on the Exact Same Obstacle Course vs. Different Mountains",
        "layman_explanation": r"""Imagine you want to know if a new running shoe (**Shoe B**) makes runners 5% faster than the old shoe (**Shoe A**):

- **The Unpaired Way (Two-Sample $Z$-Test)**: You send 100 people wearing Shoe A up a steep, rocky mountain in the rain, and 100 different people wearing Shoe B down a flat paved track in the sun. Because the terrain (task difficulty) varies wildly from person to person, the "terrain noise" drowns out the 5% shoe difference. You would need **1,375 runners per group** to be sure!
- **The Paired Way (McNemar's Test)**: You have the **exact same runner** run the **exact same obstacle block** once in Shoe A and once in Shoe B.
  - If an obstacle is super easy and they pass in both shoes $(a)$, that tells us nothing about which shoe is better—we cross it out!
  - If an obstacle is impossible and they fail in both shoes $(d)$, we cross that out too!
  - We put a magnifying glass **only on the tasks where the two agents disagreed**: where Shoe B passed and Shoe A failed ($c$, a win), versus where Shoe A passed and Shoe B failed ($b$, a regression).

### Why This Matters for AI Agents
In agent benchmarks, running both your Baseline Agent and Candidate Agent on the **exact same list of benchmark tasks** is free! By using **McNemar's Paired Test** instead of a standard unpaired A/B calculator, you cancel out task-difficulty noise and need **9.5x fewer evaluation tasks** (145 tasks instead of 1,375) to prove a 5% improvement with 80% statistical power!""",
        "hill_climbing_role": "Stage 3 — High-Sensitivity Step Verification (Detecting Incremental $+3\%$ to $+5\%$ Lifts)",
        "hill_climbing_explanation": r"""In **Agentic Hill-Climbing**, individual prompt or tool mutations rarely jump accuracy by $+30\%$ in a single bound; real progress happens through **steady $+3\%$ to $+5\%$ incremental steps** compounded over 10–20 iterations. This creates a massive statistical dilemma at every step of the climb:

- **What Breaks Without It (Blind Drift or 10x Compute Bloat)**:
  - If you use an **unpaired 2-sample $Z$-test** to verify whether a $+5\%$ candidate mutation is statistically significant ($p < 0.05$ at $80\%$ power), task-difficulty variance forces you to run **~1,375 tasks per candidate**—making a 25-step hill-climb cost over **34,000 task evaluations**!
  - Conversely, if you only run 150 tasks *without* paired testing, your statistical power drops below **15%**, meaning the hill-climber rejects 85% of genuinely good mutations and wanders randomly!
- **How It Supercharges the Hill-Climber**:
  1. **McNemar's Paired Test on Discordant Tasks ($b$ vs. $c$)** conditions on exact task IDs, canceling out shared task-difficulty variance and achieving $80\%$ power in **~145 paired tasks (a 9.5x reduction in sample size per hill-climbing step)**.
  2. **Wilcoxon Signed-Rank Guardrail for Cost/Latency**: Ensures a candidate prompt that passes McNemar's accuracy test isn't secretly achieving that lift by exploding median token consumption or getting stuck in heavy-tailed retry loops.""",
        "glossary": [
            ("Statistical Power ($1 - \\beta$)", "The probability (typically set to 80%) that your experiment will successfully detect a real improvement if one actually exists."),
            ("Significance Level ($\\alpha$)", "The false-positive risk (typically 5%, or $p < 0.05$)—the chance of claiming a prompt is better when it was just a lucky coin flip."),
            ("Concordant Pairs ($a$ and $d$)", "Tasks where both Baseline and Candidate passed ($a$) or both failed ($d$). They tie and provide zero signal about which agent is better."),
            ("Discordant Pairs ($b$ and $c$)", "The 'tie-breaker' tasks! $b$ = regressions (Baseline passed, Candidate failed); $c$ = new wins (Baseline failed, Candidate passed)."),
            ("McNemar's Test", "A statistical test for paired pass/fail data that compares new wins ($c$) against regressions ($b$) on the exact same task set."),
            ("Wilcoxon Signed-Rank Test", "A paired test for continuous numbers (like token cost or latency) that ranks differences instead of averaging them, so one huge 50,000-token outlier doesn't ruin your test."),
        ],
        "math": r"""- **McNemar's Paired Test with Edwards' Continuity Correction**:
  $$\chi^2_{\text{McNemar}} = \frac{(|b - c| - 1)^2}{b + c} \sim \chi^2_1$$
  where $b$ is the count of regressions (Baseline Pass, Candidate Fail) and $c$ is the count of newly solved tasks (Baseline Fail, Candidate Pass).
- **Paired Sample Size Formula (Connor, 1987)**:
  $$N_{\text{paired}} = \frac{\left(z_{1-\alpha/2}\sqrt{\psi} + z_{1-\beta}\sqrt{\psi - \Delta^2}\right)^2}{\Delta^2}, \qquad \psi = p_b + p_c, \quad \Delta = p_c - p_b$$
  Because task outcomes are strongly correlated across identical tasks, the discordant fraction $\psi = p_b + p_c$ is much smaller than the unpaired variance $p_1(1-p_1) + p_2(1-p_2)$.""",
        "highlights": [
            "`calculate_required_sample_size`: Computes required task counts for both unpaired 2-sample $Z$-tests and paired McNemar tests.",
            "**1,000-Trial Monte Carlo Power Benchmark**: Proves that detecting a $+5\\%$ pass rate lift ($65\\% \\to 70\\%$) at $80\\%$ power requires **~145 paired tasks** with McNemar's test versus **~1,375 tasks per arm** with an unpaired $Z$-test (**9.5x sample reduction**).",
            "Applies the non-parametric **Wilcoxon Signed-Rank Test** to heavy-tailed log-normal token consumption distributions.",
        ],
        "chart_walkthrough": """- **Left Panel (Statistical Power vs. Sample Size)**: Compare how steep the blue curve (**Paired McNemar Test**) climbs compared to the orange curve (**Unpaired 2-Sample Z-Test**). McNemar hits the 80% power line at just $N=145$ tasks, while the unpaired test needs $N=1,375$ tasks!
- **Center Panel ($2\\times 2$ Contingency Table)**: Shows a 300-task experiment. Most tasks sit in the green diagonal ("Both Pass: 185" and "Both Fail: 78"). McNemar zooms in exclusively on the off-diagonal boxes: **31 New Wins ($c$)** vs. **6 Regressions ($b$)**, yielding $p = 0.00007$.
- **Right Panel (Skewed Token Distribution)**: Token usage in agents has a long "heavy tail" when an agent gets stuck in a retry loop. The Wilcoxon test cleanly detects the median token reduction without getting skewed by extreme outliers.""",
        "references": [
            "**McNemar, Q. (1947).** *Note on the sampling error of the difference between correlated proportions or percentages.* Psychometrika, 12(2), 153–157. [https://doi.org/10.1007/BF02295996](https://doi.org/10.1007/BF02295996)",
            "**Dietterich, T. G. (1998).** *Approximate Statistical Tests for Comparing Supervised Classification Learning Algorithms.* Neural Computation, 10(7), 1895–1923. — Classic machine learning paper demonstrating why McNemar's test is ideal for expensive benchmark evaluations.",
            "**Dror, R., Baumer, G., Shlomov, S., & Reichart, R. (2018).** *The Hitchhiker's Guide to Testing Statistical Significance in Natural Language Processing.* ACL 2018. [https://aclanthology.org/P18-1128/](https://aclanthology.org/P18-1128/)",
            "**Wilcoxon, F. (1945).** *Individual Comparisons by Ranking Methods.* Biometrics Bulletin, 1(6), 80–83.",
        ],
    },
    {
        "num": 4,
        "slug": "04_multi_knob_attribution",
        "title": "Chapter 4: Multi-Knob Attribution & Multiple Regression",
        "module": "agent_stats/ch04_multi_knob_regression.py",
        "figure": "ch04_multi_knob_response_surface.png",
        "concept_img": "ch04_concept.jpg",
        "summary": (
            "Fits a second-order polynomial response surface (`statsmodels` Formula OLS) across three continuous "
            "agent harness knobs (`thinking_budget`, `context_chunks`, `tool_timeout`) to isolate linear gains, "
            "quadratic overthinking decay, and parameter interaction synergies."
        ),
        "metaphor_title": "Tuning an Espresso Machine & Avoiding the 'Overthinking Cliff'",
        "layman_explanation": r"""Imagine tuning three dials on a high-end espresso machine—**Water Temperature**, **Grind Size**, and **Brew Pressure**—or adjusting dials on a studio mixing board:

1. **Diminishing Returns & The Overthinking Cliff (Quadratic Term $\beta_{T^2} < 0$)**: Adding a little more coffee or brewing a little longer makes the espresso richer. But if you keep turning the dial to the maximum, you burn the coffee! Similarly, giving an AI agent more **Thinking Budget** helps up to ~2,700 tokens, but beyond that, the agent enters **"analysis paralysis"** (second-guessing itself, hallucinating edge cases, and degrading accuracy).
2. **Synergy Boost (Interaction Term $\beta_{TC} > 0$)**: What happens if you give an agent a massive **Thinking Budget** ($T$), but only 1 **Context Chunk** ($C$) of documentation? It has plenty of brainpower, but nothing to read! Conversely, if you dump 20 chunks of documentation into the prompt with almost zero thinking budget, it can't synthesize them. Only when you turn **both dials up together** ($T \times C$) do you unlock a synergy bonus.

### Why This Matters for AI Agents
Most engineers tune one knob at a time ("Let's set `thinking_budget=4000` and see what happens"). One-at-a-time tuning misses interactions and wastes money on over-allocated tokens. **Response Surface Methodology (RSM)** maps the entire 3D mountain peak so you can find the exact mathematical sweet spot.""",
        "hill_climbing_role": "Stage 4 — Multi-Knob Gradient Ascent & Interaction Attribution (Tuning the Continuous Harness)",
        "hill_climbing_explanation": r"""**Agentic Hill-Climbing** isn't limited to editing prompt text—a major part of climbing an agent harness is tuning continuous system parameters (`thinking_budget`, `context_chunks` top-$k$, `temperature`, `tool_timeout`).

- **What Breaks Without It (One-Factor-at-a-Time Blindness & Overthinking)**:
  - **Missing Synergies**: If a hill-climber increases `context_chunks` from 5 to 15 while keeping `thinking_budget` stuck at 500 tokens, pass rate barely moves (or drops due to context overload), causing the hill-climber to falsely conclude *"more RAG context doesn't help."* It missed the positive **interaction term ($\beta_{TC} > 0$)**!
  - **Climbing Over the Cliff**: Assuming *"more thinking tokens is always better"* leads hill-climbers to max out `thinking_budget=4000`, paying 50% more token cost while suffering **quadratic overthinking decay ($\beta_{T^2} < 0$)**.
- **How It Supercharges the Hill-Climber**:
  By fitting a **Second-Order Polynomial Response Surface** across past hill-climbing runs, the optimizer estimates the exact gradient vector and Hessian curvature matrix—allowing it to solve $\nabla \text{PassRate}(T^*, C^*) = \mathbf{0}$ and jump directly to the joint sweet spot (`~2,690 thinking tokens`, `~14.1 context chunks`).""",
        "glossary": [
            ("Response Surface Methodology (RSM)", "Fitting a smooth curved 3D surface (like a topographic mountain map) to experimental data so you can locate the highest performance peak."),
            ("Linear Effect ($\\beta_T, \\beta_C$)", "The initial upward slope—how much pass rate improves per unit when you first start increasing a knob."),
            ("Quadratic Decay ($\\beta_{T^2}, \\beta_{C^2}$)", "The curvature ($T^2$) that bends the line downward into an upside-down U-shape (parabola), capturing diminishing returns and 'overthinking'."),
            ("Interaction Term ($\\beta_{TC} \\cdot T \\cdot C$)", "Measures **synergy**: when two knobs together produce a bigger boost than the sum of turning each knob alone."),
            ("Stationary Optimum ($T^*, C^*$)", "The exact coordinates of the mountain peak where the slope flattens out to zero ($\\nabla = 0$) before curving downward."),
            ("$R^2$ (Coefficient of Determination)", "The percentage of variation in pass rates explained by our regression equation (here, $94.2\\%$)."),
        ],
        "math": r"""- **Second-Order Response Surface Model**:
  $$\text{PassRate} = \beta_0 + \underbrace{\beta_T T + \beta_C C + \beta_S S}_{\text{Linear Main Effects}} + \underbrace{\beta_{T^2} T^2 + \beta_{C^2} C^2}_{\text{Quadratic Decay (Overthinking)}} + \underbrace{\beta_{TC}(T \cdot C)}_{\text{Synergy Interaction}} + \epsilon$$
- **Finding the Sweet Spot Peak $(T^*, C^*)$ via First-Order Partial Derivatives**:
  Setting $\frac{\partial \text{PassRate}}{\partial T} = 0$ and $\frac{\partial \text{PassRate}}{\partial C} = 0$ gives a $2\times 2$ linear system:
  $$\begin{bmatrix} 2\beta_{T^2} & \beta_{TC} \\ \beta_{TC} & 2\beta_{C^2} \end{bmatrix} \begin{bmatrix} T^* \\ C^* \end{bmatrix} = \begin{bmatrix} -\beta_T \\ -\beta_C \end{bmatrix}$$""",
        "highlights": [
            "Fits a full quadratic + interaction OLS regression ($R^2 = 0.94$) with $t$-statistics, $p$-values, and confidence intervals.",
            "Renders 3D surface plots and 2D iso-performance contour maps pinpointing the stationary optimum (~2,690 thinking tokens, ~14.1 context chunks).",
            "Automatically extracts plain-English developer insights quantifying the marginal efficiency loss per 100 tokens past the overthinking threshold.",
        ],
        "chart_walkthrough": """- **Left Panel (3D Response Surface)**: Look at the curved mountain surface. Notice how moving from left to right along `Thinking Budget` climbs steeply up to ~2,690 tokens (marked by the red star) and then **curves downward**—that downward slope on the right is the "Overthinking Cliff."
- **Right Panel (2D Topographic Contour Map)**: Just like a hiker's elevation map, the concentric rings show equal pass-rate zones. The bright yellow-green center with the red star (`Optimum: 2690 tok, 14.1 chunks`) shows the exact harness configuration that maximizes accuracy (~86%) without wasting tokens.""",
        "references": [
            "**Box, G. E. P., & Wilson, K. B. (1951).** *On the Experimental Attainment of Optimum Conditions.* Journal of the Royal Statistical Society: Series B, 13(1), 1–38. — The foundational paper introducing Response Surface Methodology (RSM).",
            "**Montgomery, D. C. (2019).** *Design and Analysis of Experiments (10th ed.).* Wiley.",
            "**Cuadron, A., et al. (2025).** *The Danger of Overthinking: Examining the Reasoning-Action Dilemma in Agentic Tasks.* arXiv:2502.08235. [https://arxiv.org/abs/2502.08235](https://arxiv.org/abs/2502.08235) — Empirical study showing how excessive reasoning budgets degrade agent task performance.",
        ],
    },
    {
        "num": 5,
        "slug": "05_bayesian_sequential_testing",
        "title": "Chapter 5: Bayesian Sequential Testing & Early Stopping",
        "module": "agent_stats/ch05_bayesian_sequential.py",
        "figure": "ch05_bayesian_sequential_stopping.png",
        "concept_img": "ch05_concept.jpg",
        "summary": (
            "Implements conjugate Beta-Binomial posterior updating and sequential early stopping (`BetaBinomialEvaluator`) "
            "to prune weak prompt candidates early and accept strong winners without running fixed $N=500$ sweeps."
        ),
        "metaphor_title": "The Restaurant Taste-Tester: Why Eat 500 Spoonfuls of Burnt Soup?",
        "layman_explanation": r"""Imagine a chef testing 100 experimental soup recipes. In a rigid traditional evaluation (**Fixed-Horizon Testing**), the rule says: *"You must eat 500 spoonfuls of every single recipe before you are allowed to say whether it is good or bad."*

If Recipe #1 tastes like burnt rubber on the first 25 spoonfuls, why on earth would you force yourself to eat 475 more spoonfuls?! Conversely, if Recipe #99 is unmistakably delicious after 90 spoonfuls, you don't need 410 more to crown it a winner.

### How Bayesian Sequential Updating Works
Instead of waiting until Trial 500 to look at the score, **Bayesian Sequential Testing** maintains a living "belief curve" (**Beta Distribution**) for the Candidate and the Baseline after **every single task**:
- At **Trial 0**, both curves are wide and flat (*"We know nothing yet"*).
- After each task, if the agent passes, the curve shifts right and gets narrower; if it fails, it shifts left.
- At every step, we calculate the overlap: **What is the probability $P(\theta_{\text{cand}} > \theta_{\text{base}})$ that the Candidate is genuinely better than the Baseline?**
  - If that probability drops below **10%** ($P \le 0.10$), we **Early Abandon** immediately!
  - If that probability climbs above **95%** ($P \ge 0.95$), we **Early Accept** and celebrate!

Across a typical portfolio of 100 weak prompt ideas and 10 strong ones, this saves **~74% of your LLM token budget and wall-clock time**.""",
        "hill_climbing_role": "Stage 5 — The High-Velocity Inner-Loop Filter (`SEQUENTIAL_EXEC` Early Pruning)",
        "hill_climbing_explanation": r"""In an autonomous **Agentic Hill-Climbing** harness (such as `agentic-harness-hill-climbing`, AlphaEvolve, or OPRO), **85% to 90% of candidate mutations generated during search are regressions or no-ops** (e.g., a prompt edit that accidentally breaks tool formatting or adds unhelpful verbosity).

- **What Breaks Without It (Compute Starvation)**: If your hill-climber runs all $N=500$ benchmark tasks to completion on every single dead-end candidate, evaluating 110 mutations requires **55,000 full agent trajectories**. At 30 seconds per agent trajectory, your hill-climber stalls for days spending 90% of its GPU/API budget testing already-broken candidates!
- **How It Supercharges the Hill-Climber**:
  1. **Real-Time Pruning (`ABANDON` at $P \le 0.10$)**: By streaming task completions into `BetaBinomialEvaluator.step()`, bad mutations are mathematically identified and killed after just **20–35 tasks**, freeing the worker pool immediately to test the next candidate mutation.
  2. **4x Faster Hill-Climbing Velocity**: Cutting total benchmark evaluations from **55,000 down to 14,193 (~74.2% compute savings)** means your hill-climber can explore **nearly 4x as many evolutionary generations** in the exact same wall-clock window and token budget!""",
        "glossary": [
            ("Prior Distribution $\\text{Beta}(\\alpha_0, \\beta_0)$", "Your starting belief about an agent's pass rate before running any tasks. $\\text{Beta}(1, 1)$ is a completely flat line from 0% to 100% ('total open mind')."),
            ("Posterior Distribution $\\text{Beta}(\\alpha_0 + s, \\beta_0 + f)$", "Your updated belief curve after observing $s$ passes and $f$ failures. As more data arrives, the bell curve gets taller and skinnier."),
            ("Conjugate Prior", "A mathematical superpower where the updated belief (Posterior) has the exact same formula family (Beta) as the starting belief (Prior)—meaning updating takes 1 line of addition (`alpha += 1`) with zero slow simulations!"),
            ("Probability of Superiority $P(\\theta_C > \\theta_B \\mid D)$", "The exact percentage chance (from 0% to 100%) that the Candidate's true pass rate beats the Baseline's true pass rate, given the trials seen so far."),
            ("Early Abandon / Early Accept", "Stopping rules that kill hopeless prompts early ($P \\le 0.10$) and promote clear winners early ($P \\ge 0.95$)."),
        ],
        "math": r"""- **Closed-Form Conjugate Posterior Update**:
  Starting with uniform prior $\text{Beta}(\alpha_0=1, \beta_0=1)$, after $s$ successes and $n-s$ failures in $n$ trials:
  $$\theta \mid (s, n) \sim \text{Beta}(\alpha_0 + s, \, \beta_0 + n - s)$$
- **Posterior Probability of Superiority**:
  Computed exactly via 1D numerical integration (where $f_{\text{Beta}}$ is the PDF and $F_{\text{Beta}}$ is the CDF):
  $$P(\theta_{\text{cand}} > \theta_{\text{base}} \mid D) = \int_0^1 f_{\text{Beta}}(x; \alpha_C, \beta_C) F_{\text{Beta}}(x; \alpha_B, \beta_B) \, dx$$""",
        "highlights": [
            "Computes $P(\\theta_{\\text{cand}} > \\theta_{\\text{base}} \\mid D)$ via both **exact 1D numerical quadrature** (`scipy.integrate.quad`) and **Monte Carlo sampling** (`numpy`).",
            "`BetaBinomialEvaluator`: Stateful step-by-step evaluator with configurable boundaries (`ACCEPT` at $P \\ge 0.95$, `ABANDON` at $P \\le 0.10$, else `CONTINUE`).",
            "**Compute-Savings Benchmark**: Across 100 weak variants and 10 strong variants, Bayesian early stopping reduces total evaluation trials by **~74%** compared to fixed $N=500$ sweeps.",
        ],
        "chart_walkthrough": """- **Left Panel (Posterior Evolution)**: Watch the orange (Baseline) and blue (Candidate) curves as trials arrive (from top to bottom: $t=10, 30, 80, 150$). At $t=10$, the curves are wide and overlap heavily ($P=73.9\\%$). By $t=150$, both curves have tightened into sharp peaks with minimal overlap ($P=98.3\\%$), crossing the 95% threshold!
- **Center Panel (Sequential Decision Trajectories)**: The green line (Strong Candidate) climbs steadily and hits the green `Early Accept` line around step 90. The red line (Weak Candidate) plunges below the red `Early Abandon` line before step 30—saving 470 wasted trials!
- **Right Panel (Compute Savings Benchmark)**: Evaluating 110 candidates at a fixed 500 tasks each costs **55,000 task runs**. Bayesian Sequential Stopping finishes the exact same portfolio in **14,193 task runs—a 74.2% reduction in compute cost!**""",
        "references": [
            "**Wald, A. (1945).** *Sequential Tests of Statistical Hypotheses.* The Annals of Mathematical Statistics, 16(2), 117–186. — The foundational paper on Sequential Probability Ratio Testing (SPRT).",
            "**Scott, S. L. (2010).** *A modern Bayesian look at the multi-armed bandit.* Applied Stochastic Models in Business and Industry, 26(6), 639–658. — Explains Beta-Binomial probability of superiority used across Google Analytics experiments.",
            "**Miller, E. (2015).** *Simple Sequential A/B Testing.* Evan Miller's Statistical Tools. [https://www.evanmiller.org/sequential-ab-testing.html](https://www.evanmiller.org/sequential-ab-testing.html)",
            "**Kruschke, J. K. (2014).** *Doing Bayesian Data Analysis: A Tutorial with R, JAGS, and Stan (2nd ed.).* Academic Press.",
        ],
    },
    {
        "num": 6,
        "slug": "06_hierarchical_bayesian_modeling",
        "title": "Chapter 6: Hierarchical Bayesian Modeling for Edge Cases",
        "module": "agent_stats/ch06_hierarchical_bayes.py",
        "figure": "ch06_hierarchical_forest_plot.png",
        "concept_img": "ch06_concept.jpg",
        "summary": (
            "Demonstrates Empirical Bayes partial pooling and shrinkage across 8 agent failure categories with "
            "uneven sample sizes ($N_j \\in [3, 150]$), preventing false regression panic on sparse edge-case slices."
        ),
        "metaphor_title": "The Opening-Day Baseball Batting Average: Borrowing Strength from the League",
        "layman_explanation": r"""Imagine it is Opening Day of the baseball season. A rookie steps up to the plate 3 times and strikes out all 3 times ($0 / 3 = 0.000$ batting average).

- **No Pooling (Panic Mode)**: Looking only at those 3 swings, a naive manager screams: *"His true skill is 0%! Cut him from the roster immediately!"*
- **Complete Pooling (Blind Mode)**: Ignoring the 3 strikeouts completely and saying: *"Every player in Major League Baseball bats .260, so he is a .260 hitter."*
- **Partial Pooling / Bayesian Shrinkage (The Smart Scout)**: A seasoned scout says: *"Three swings is tiny evidence. Since the league average is .260, my best estimate of his true skill right now is pulled (shrunk) strongly toward the league average—around .235. Once he has 150 at-bats, we'll trust his personal stats almost completely."*

### Why This Matters for AI Agents
When you slice an agent benchmark into fine-grained failure categories (e.g., `sql_generation` with $N=150$ tasks vs. `distributed_race_condition` with only $N=3$ tasks), a single unlucky failure in a 3-task category drops the raw pass rate by **33%**! Without **Hierarchical Bayesian Shrinkage**, engineering teams waste days chasing phantom "0% pass rate" emergencies in tiny categories that are just small-sample noise.""",
        "hill_climbing_role": "Stage 6 — Multi-Slice Regression Guardrail (Preventing 'Edge-Case Whiplash' During the Climb)",
        "hill_climbing_explanation": r"""Production **Agentic Hill-Climbing** harnesses don't just optimize one global number—they enforce **per-category non-regression constraints** across 10 to 30 behavioral slices (e.g., *"Promote the candidate prompt only if overall accuracy improves AND no individual domain slice regresses by more than 10%"*).

- **What Breaks Without It (Edge-Case Whiplash & False Vetoes)**:
  - Many critical edge-case slices (`distributed_race_condition`, `memory_leak`) only have $N=3$ or $N=4$ tasks in the benchmark. A single random failure swings the raw unpooled pass rate from `33.3%` down to `0.0%` (`-33.3 pp`!).
  - **False Vetoes**: A naive hill-climber sees the `-33.3 pp` drop on that 3-task slice and **vetoes a brilliant candidate prompt** that actually improved the 150-task core categories by $+8\%$.
  - **Prompt Whiplash**: Even worse, if an LLM meta-optimizer sees `distributed_race_condition = 0.0%`, it over-corrects by stuffing the system prompt with race-condition instructions, breaking SQL and API tool calling on the next step!
- **How It Supercharges the Hill-Climber**:
  **Hierarchical Bayesian Partial Pooling** shrinks sparse slices toward the global hyperprior mean ($\mu_0$) using weight $B_j = \frac{\kappa}{\kappa + N_j}$—pulling a noisy `0/3 (0.0%)` slice to a realistic **56.8%** while leaving $N=150$ categories anchored to their empirical data. This cuts category estimation RMSE by **68%** and eliminates false-alarm vetoes during multi-slice hill-climbing.""",
        "glossary": [
            ("No Pooling ($S_j / N_j$)", "Calculating each category's pass rate in total isolation. Highly accurate for huge categories ($N=150$), wildly noisy for tiny categories ($N=3$)."),
            ("Complete Pooling", "Lumping all tasks together into one global average ($68.2\\%$), ignoring real differences between easy and hard categories."),
            ("Partial Pooling (Hierarchical Bayes)", "The gold-standard compromise: each category gets a weighted blend between its own raw score and the global average, weighted by how much data ($N_j$) it has."),
            ("Shrinkage Factor ($B_j = \\frac{\\kappa}{\\kappa + N_j}$)", "The 'magnetic pull' toward the global average. When sample size $N_j=3$ is tiny, $B_j \\approx 83\\%$ (strong pull to the global mean). When $N_j=150$ is huge, $B_j \\approx 9\\%$ (stays anchored to its own data)."),
            ("Hyperprior ($\\mu_0, \\kappa$)", "The overarching 'league average' ($\\mu_0$) and consistency strength ($\\kappa$) learned automatically across all categories."),
            ("Credible Interval (95% CI)", "The horizontal error bar showing the 95% likely range of a category's true pass rate."),
        ],
        "math": r"""- **Two-Level Hierarchical Beta-Binomial Model**:
  $$\theta_j \sim \text{Beta}(\alpha_0, \beta_0), \qquad S_j \mid \theta_j \sim \text{Binomial}(N_j, \theta_j)$$
- **Posterior Shrinkage Formula (Weighted Average of Global Prior and Local Data)**:
  $$\mathbb{E}[\theta_j \mid S_j, N_j] = \underbrace{\left(\frac{\kappa}{\kappa + N_j}\right)}_{B_j \text{ (Shrinkage Weight)}} \mu_0 + (1 - B_j)\left(\frac{S_j}{N_j}\right), \qquad \kappa = \alpha_0 + \beta_0$$
  Notice how as $N_j \to 0$, $B_j \to 1$ (estimate equals the global mean $\mu_0$). As $N_j \to \infty$, $B_j \to 0$ (estimate equals the raw category rate $S_j/N_j$).""",
        "highlights": [
            "Compares **No Pooling** ($S_j/N_j$), **Complete Pooling** ($\\sum S_j / \\sum N_j$), and **Partial Pooling** (Empirical Bayes marginal likelihood maximization).",
            "Demonstrates how `distributed_race_condition` ($N=3, S=0$, raw $0.0\\%$) and `memory_leak` ($N=4, S=1$, raw $25.0\\%$) are shrunk toward the population hyperprior mean ($56.8\\%$ and $59.9\\%$).",
            "Reduces category pass-rate estimation RMSE against true latent capability by **68%** compared to raw unpooled proportions.",
        ],
        "chart_walkthrough": """- **Left Panel (Forest Plot of 8 Categories)**:
  - Look at the top two rows (`distributed_race_condition [N=3]` and `memory_leak [N=4]`): The red hollow circles (**No Pooling Raw**) sit way out at **0%** and **25%** with gigantic error bars. The green squares (**Hierarchical Partial Pooling**) pull them right back to **56.8%** and **59.9%**—right next to the **True Latent Capability** (black diamonds)!
  - Now look at the bottom row (`sql_generation [N=150]`): Because $N=150$ is huge, the green square stays right on top of the red circle (~81%), barely moving at all!
- **Right Panel (Shrinkage Factor Curve)**: Shows the exact mathematical curve $B_j = \\frac{\\kappa}{\\kappa + N_j}$. Small categories on the left get >78% shrinkage pull; large categories on the right get <10% pull.""",
        "references": [
            "**Efron, B., & Morris, C. (1977).** *Stein's Paradox in Statistics.* Scientific American, 236(5), 119–127. — The famous paper using baseball batting averages to explain why shrinkage estimators beat raw averages.",
            "**Gelman, A., Carlin, J. B., Stern, H. S., Dunson, D. B., Vehtari, A., & Rubin, D. B. (2013).** *Bayesian Data Analysis (3rd ed., Chapter 5: Hierarchical Models).* CRC Press. [http://www.stat.columbia.edu/~gelman/book/](http://www.stat.columbia.edu/~gelman/book/)",
            "**McElreath, R. (2020).** *Statistical Rethinking: A Bayesian Course with Examples in R and Stan (2nd ed., Chapter 13: Models With Memory).* CRC Press.",
        ],
    },
    {
        "num": 7,
        "slug": "07_bayesian_optimization",
        "title": "Chapter 7: Bayesian Optimization with Gaussian Processes",
        "module": "agent_stats/ch07_bayesian_optimization.py",
        "figure": "ch07_bayesian_optimization_surfaces.png",
        "concept_img": "ch07_concept.jpg",
        "summary": (
            "Uses Gaussian Process Regression (`Matern(nu=2.5)` kernel) and acquisition functions (`Expected Improvement` "
            "and `GP-UCB`) to find the global optimum of an expensive black-box agent harness within 25 trials."
        ),
        "metaphor_title": "Prospecting for Gold in the Fog with a Smart Uncertainty Radar",
        "layman_explanation": r"""Imagine searching for the deepest oil reservoir across a vast mountain range covered in thick fog, where **drilling a single test well costs \$10,000** (just like running a full 500-task agent benchmark suite costs hours of GPU/API time):

- **Grid Search (The Brute-Force Way)**: Drilling a well every 100 yards on a $10 \times 10$ grid requires **100 wells (\$1,000,000)**—and 90% of those wells are wasted in flat, barren desert!
- **Bayesian Optimization (The Smart Radar)**:
  1. **The Surrogate Map (Gaussian Process)**: You drill 5 initial random wells. Between those 5 pins, the Gaussian Process draws a smooth contour map of the likely terrain (**Predicted Mean $\mu$**) AND a "Fog Thickness Map" (**Uncertainty $\sigma$**) that is zero right where you drilled and thickens in unexplored regions.
  2. **The Acquisition Compass (`Expected Improvement`)**: Where should you drill Well #6? You want a spot that either has a **high predicted score** (*Exploitation: drilling near your best discovery so far*) OR **huge uncertainty** (*Exploration: checking a big foggy corner that might hide a giant peak*). The Acquisition Function combines both into a single glowing beacon pointing to the exact most informative coordinate to test next!

Within just **25 trials** (instead of 100+ grid points), Bayesian Optimization locks onto the global peak.""",
        "hill_climbing_role": "Stage 7 — Escaping Local Optima via Sample-Efficient Global Search (`CANDIDATE_SEARCH` Engine)",
        "hill_climbing_explanation": r"""Standard greedy **Agentic Hill-Climbing** suffers from a classic fatal flaw: **getting trapped on a local hill (local optimum)**.

- **What Breaks Without It (Stuck on a Foothill)**: Suppose your agent harness has a local performance bump around `reasoning_tokens=1,200, context_limit=25k` (72% pass rate) and a much taller global peak at `reasoning_tokens=2,850, context_limit=85k` (86% pass rate), separated by a dip. A greedy local hill-climber that only takes small steps uphill climbs onto the 72% foothill, sees the score drop in every immediate direction, and stops forever—missing the 86% global peak!
- **How It Supercharges the Hill-Climber**:
  1. **Memory of Uncertainty ($\sigma(\mathbf{x})$)**: Unlike greedy hill-climbing (which only remembers the current best point), a **Gaussian Process (`Matern 5/2`) Surrogate** remembers *every* configuration tested so far and knows exactly which regions of the parameter space are still unexplored (high $\sigma$).
  2. **Automated Exploration-Exploitation Switching**: When the local hill flattens out, the **Expected Improvement (EI)** and **GP-UCB** acquisition functions automatically shift weight to the exploration term $\sigma(\mathbf{x})\phi(Z)$, launching a targeted probe across the valley to discover the true global peak within **25 evaluations**.""",
        "glossary": [
            ("Black-Box Function", "A system (like a full agent benchmark run) where you can plug in configuration numbers and observe the final pass-rate score, but you don't have a simple math formula for what happens inside."),
            ("Gaussian Process (GP) Surrogate", "A flexible statistical model that fits a smooth curve through the points you've tested so far, while also calculating a confidence band (uncertainty $\\sigma$) at every untested point."),
            ("Matérn 5/2 Kernel", "The 'smoothness rule' used by the Gaussian Process. Unlike overly smooth curves, Matérn 5/2 allows realistic bumps and sharp ridges common in ML hyperparameters."),
            ("Exploration vs. Exploitation", "The fundamental dilemma: should you test right next to your current best setting (**Exploit**) or test a totally unknown region where uncertainty is high (**Explore**)?"),
            ("Acquisition Function (`Expected Improvement` / `GP-UCB`)", "A cheap formula that scores every possible untested setting based on both its predicted mean $\\mu(x)$ and its uncertainty $\\sigma(x)$, picking the highest scorer as the next trial."),
        ],
        "math": r"""- **Matérn $\nu = 5/2$ Covariance Kernel**:
  Determines how strongly two parameter configurations $\mathbf{x}$ and $\mathbf{x}'$ correlate as a function of scaled distance $r = \|\mathbf{x} - \mathbf{x}'\|_{\mathbf{\ell}}$:
  $$k_{5/2}(r) = \sigma_f^2 \left(1 + \sqrt{5}r + \frac{5}{3}r^2\right)\exp(-\sqrt{5}r)$$
- **Expected Improvement (EI) & Upper Confidence Bound (GP-UCB)**:
  Given current best observed score $y^+$, predicted mean $\mu(\mathbf{x})$, and uncertainty $\sigma(\mathbf{x})$ (with $Z = \frac{\mu(\mathbf{x}) - y^+ - \xi}{\sigma(\mathbf{x})}$):
  $$\text{EI}(\mathbf{x}) = \underbrace{(\mu(\mathbf{x}) - y^+ - \xi)\Phi(Z)}_{\text{Exploitation Term}} + \underbrace{\sigma(\mathbf{x})\phi(Z)}_{\text{Exploration Term}}, \qquad \text{UCB}(\mathbf{x}) = \mu(\mathbf{x}) + \kappa\sigma(\mathbf{x})$$""",
        "highlights": [
            "Models the multimodal black-box objective `evaluate_harness_config(reasoning_tokens, context_limit)` using `scikit-learn` `GaussianProcessRegressor`.",
            "Iteratively balances exploration (high posterior uncertainty $\\sigma$) and exploitation (high posterior mean $\\mu$) over 25 evaluations.",
            "Renders side-by-side GP Posterior Mean/Uncertainty contours and Expected Improvement acquisition surfaces at Trials 5, 12, and 25.",
        ],
        "chart_walkthrough": """- **Top Row (Gaussian Process Predicted Mean & Uncertainty)**: Read from left to right (`Trial 5` $\\to$ `Trial 12` $\\to$ `Trial 25`). At `Trial 5`, with only 5 white dots tested, the GP map is blurry and rough. By `Trial 12` and `Trial 25`, the optimizer has concentrated sample dots around the true peak (gold star at ~2,850 tokens, ~85 KB context), bringing the discovered best (cyan star) right onto the global maximum!
- **Bottom Row (Expected Improvement Acquisition Surface)**: Bright yellow regions show where the optimizer wants to sample next (marked by the red triangle $\\blacktriangle$). Notice how as regions are explored, their Expected Improvement drops to dark purple, pushing the red triangle to remaining promising zones until convergence.""",
        "references": [
            "**Snoek, J., Larochelle, H., & Adams, R. P. (2012).** *Practical Bayesian Optimization of Machine Learning Algorithms.* NeurIPS 2012. [https://arxiv.org/abs/1206.2944](https://arxiv.org/abs/1206.2944) — The landmark paper that popularized GP Bayesian Optimization with Matérn 5/2 kernels for ML hyperparameter tuning.",
            "**Shahriari, B., Swersky, K., Wang, Z., Adams, R. P., & de Freitas, N. (2016).** *Taking the Human Out of the Loop: A Review of Bayesian Optimization.* Proceedings of the IEEE, 104(1), 148–175.",
            "**Rasmussen, C. E., & Williams, C. K. I. (2006).** *Gaussian Processes for Machine Learning.* MIT Press. [http://www.gaussianprocess.org/gpml/](http://www.gaussianprocess.org/gpml/)",
            "**Garnett, R. (2023).** *Bayesian Optimization.* Cambridge University Press. [https://bayesoptbook.com/](https://bayesoptbook.com/)",
        ],
    },
    {
        "num": 8,
        "slug": "08_failure_trace_clustering",
        "title": "Chapter 8: Failure Trace Mining & Unsupervised Clustering",
        "module": "agent_stats/ch08_trace_clustering.py",
        "figure": "ch08_failure_trace_clusters.png",
        "concept_img": "ch08_concept.jpg",
        "summary": (
            "Parses 300 raw agent failure logs (`stdout`/`stderr`, tool payloads, stack traces), vectorizes them "
            "with sublinear TF-IDF, clusters failure modes via PCA + $k$-Means, and synthesizes actionable System Prompt "
            "Negative Constraints."
        ),
        "metaphor_title": "Sorting a Mountain of 300 Crash Receipts into 5 Neat Diagnostic Folders",
        "layman_explanation": r"""Imagine your AI agent runs overnight on 1,000 tasks and produces **300 failed crash logs**—each a 40-line wall of messy stack traces, JSON payloads, and error codes.

No human engineer wants to read 300 raw stack traces line by line on Monday morning. Worse, if you just read the first 3 logs, you might think the whole system is failing due to API Timeouts, missing the fact that 60% of the crashes are actually caused by the agent inventing a fake tool parameter!

### How Unsupervised Trace Mining Works
Instead of reading 300 logs manually, we build an automated "Prism" that sorts the pile into distinct root-cause buckets without needing pre-existing labels:
1. **Highlight the Rare Diagnostic Words (`TF-IDF`)**: Every log contains boring boilerplate words like `ERROR`, `Traceback`, `agent_runner.py`. **TF-IDF** automatically mutes words that appear in every log and boosts words that uniquely identify a specific crash (like `429DEADLINE_EXCEEDED`, `maximum_context_length`, or `AdditionalPropertiesError`).
2. **Group into Constellations (`PCA + k-Means`)**: Logs with similar error signatures are pulled into 5 tight geometric clusters.
3. **Pick the Single Best Representative (`Cluster Medoid`)**: Instead of reading 60 logs in Cluster #1, the math finds the single real log sitting closest to the exact center of that cluster (**the Medoid**) and writes a **System Prompt Guardrail** to fix all 60 failures at once!""",
        "hill_climbing_role": "Stage 8 — Closing the Loop: Directed Mutation Generation (`TRACE_DIAGNOSIS` $\\to$ Next Candidate)",
        "hill_climbing_explanation": r"""How does an **Agentic Hill-Climber** decide *what* to change in the prompt or harness for the next iteration?

- **What Breaks Without It (Blind Random Walk vs. Context-Overflow Bias)**:
  - **Blind Mutation**: If the hill-climber simply asks an LLM to *"rephrase the system prompt to make it better"* without diagnostic feedback, it performs a blind random walk—wasting dozens of steps guessing what might be wrong.
  - **Recency / Sample Bias**: Conversely, if you dump 300 raw failure logs into a meta-optimizer LLM, you either overflow the context window or bias the LLM toward fixing whichever 2 or 3 failures happened to appear last in the prompt!
- **How It Supercharges the Hill-Climber**:
  1. **Quantitative Pareto Prioritization**: **Sublinear TF-IDF + $k$-Means** groups all 300 failures from the current hill-climbing evaluation into $K$ distinct failure archetypes (`ARI = 1.000`) and ranks them by exact cluster volume (e.g., *"Cluster C2: Tool Schema Hallucination accounts for 24% of all failures"*).
  2. **Medoid-Grounded Prompt Synthesis**: By feeding the meta-optimizer **only the 5 Cluster Medoid traces + top TF-IDF diagnostic tokens**, the hill-climber synthesizes targeted **System Prompt Negative Constraints** that directly eliminate the dominant failure modes on the very next climb step!""",
        "glossary": [
            ("TF-IDF (Term Frequency–Inverse Document Frequency)", "A text-scoring formula that gives high weight to specific error tokens (like `PermissionError` or `LoopDetectedError`) and near-zero weight to common boilerplate words that appear in every log."),
            ("Sublinear TF Scaling ($1 + \\log \\text{tf}$)", "Prevents a single error word repeated 50 times in a stack-overflow loop from dominating the entire vector."),
            ("PCA (Principal Component Analysis)", "A dimensionality-reduction technique that squashes a 500-word vocabulary space down into a 2D map ($x, y$) so we can visualize the clusters on a scatter plot."),
            ("$k$-Means Clustering", "An unsupervised algorithm that automatically groups the 300 logs into $k$ neighborhoods based on their cosine/Euclidean similarity."),
            ("Silhouette Score", "A quality score from $-1$ to $+1$ measuring how tightly packed each cluster is and how cleanly separated it is from neighboring clusters. The spike at $k=5$ tells us there are exactly 5 failure modes!"),
            ("Cluster Medoid", "The single actual failure log sitting closest to the mathematical center (centroid) of a cluster—the best 'textbook example' for an engineer or meta-optimizer to inspect."),
        ],
        "math": r"""- **Sublinear TF-IDF Vectorization**:
  For term $t$ in failure log $d$ across $N$ total failure logs:
  $$\text{tfidf}(t, d) = \big(1 + \log \text{tf}(t, d)\big) \cdot \left(\log \frac{1 + N}{1 + \text{df}(t)} + 1\right)$$
- **Cluster Medoid Representative Selection**:
  Finds the real failure log $i \in C_k$ closest to the cluster centroid $\boldsymbol{\mu}_k$:
  $$\text{medoid}(k) = \arg\min_{i \in C_k} \|\mathbf{v}_i - \boldsymbol{\mu}_k\|_2$$""",
        "highlights": [
            "Synthesizes 300 realistic multi-line failure logs across 5 error archetypes: `Tool Schema Hallucination`, `Context Length Exceeded`, `API Timeout`, `Environment Permission Denied`, and `Infinite Loop`.",
            "Separates all 5 archetypes via unsupervised TF-IDF + $k$-Means (`Adjusted Rand Index = 1.000`, `Silhouette Score = 0.432`).",
            "Extracts centroid diagnostic keywords, medoid stack traces, and auto-generated **System Prompt Negative Constraints**, exporting both static PNG and interactive Plotly HTML scatter plots.",
        ],
        "chart_walkthrough": """- **Left Panel (PCA 2D Projection of 300 Logs)**: Each dot is one raw crash log. Notice how TF-IDF + PCA cleanly separates the 300 messy text logs into **5 distinct islands** (`C0` through `C4`). The black `X` in the center of each island marks its **Medoid**—the single representative trace you need to read.
- **Right Panel (Silhouette Score Model Selection)**: How does an automated pipeline know whether there are 3, 5, or 8 bug types in last night's run? By plotting the **Silhouette Score** across $k=2\\dots 8$, the sharp peak at **$k=5$** (`0.432`) automatically discovers the exact number of underlying failure archetypes!""",
        "references": [
            "**Salton, G., & Buckley, C. (1988).** *Term-weighting approaches in automatic text retrieval.* Information Processing & Management, 24(5), 513–523. — Foundational work on TF-IDF vectorization.",
            "**Rousseeuw, P. J. (1987).** *Silhouettes: A graphical aid to the interpretation and validation of cluster analysis.* Journal of Computational and Applied Mathematics, 20, 53–65.",
            "**Cemri, M., Pan, M. Z., Yang, S., et al. (2025).** *Why Do Multi-Agent LLM Systems Fail? (MAST Taxonomy).* arXiv:2503.13657. [https://arxiv.org/abs/2503.13657](https://arxiv.org/abs/2503.13657) — Automated trace taxonomy and failure clustering for LLM agent systems.",
            "**Manning, C. D., Raghavan, P., & Schütze, H. (2008).** *Introduction to Information Retrieval.* Cambridge University Press. [https://nlp.stanford.edu/IR-book/](https://nlp.stanford.edu/IR-book/)",
        ],
    },
]


def build_layman_notebook_markdown(spec: dict, img_prefix: str) -> str:
    """Builds the rich Layman's Guide + Hill-Climbing Relevance + Concept Visual + Glossary + References cell."""
    glossary_rows = "\n".join([f"| **{term}** | {desc} |" for term, desc in spec["glossary"]])
    refs = "\n".join([f"- {r}" for r in spec["references"]])
    return f"""## 🧠 Layman's Guide: {spec['metaphor_title']}

![{spec['title']} — Concept Illustration]({img_prefix}/figures/concepts/{spec['concept_img']})

{spec['layman_explanation']}

---

### 🧗 Why This Matters for Agentic Hill-Climbing
> **Hill-Climbing Role**: *{spec['hill_climbing_role']}*

{spec['hill_climbing_explanation']}

---

### 📖 Plain-English Terminology & Jargon Buster

| Term / Symbol | Plain-English Meaning |
| :--- | :--- |
{glossary_rows}

### 📚 Resources & Deeper Reading
{refs}
"""


def inject_layman_cell_into_notebook(nb_path: Path, spec: dict, img_prefix: str) -> None:
    """Inserts or updates the Layman's Guide markdown cell right after cell 0 in an executed .ipynb file."""
    data = json.loads(nb_path.read_text(encoding="utf-8"))
    cells = data.get("cells", [])
    layman_md = build_layman_notebook_markdown(spec, img_prefix)
    new_cell = {
        "cell_type": "markdown",
        "id": f"layman-guide-ch{spec['num']:02d}",
        "metadata": {},
        "source": [line + "\n" for line in layman_md.splitlines()],
    }
    if len(cells) > 1 and cells[1].get("id", "").startswith("layman-guide-"):
        cells[1] = new_cell
    else:
        cells.insert(1, new_cell)
    data["cells"] = cells
    nb_path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    for spec in CHAPTER_SPECS:
        slug = spec["slug"]
        ch_dir = CHAPTERS_DIR / slug
        ch_dir.mkdir(parents=True, exist_ok=True)

        # 1. Update root notebook with layman + hill-climbing guide (using ./figures/... path)
        root_nb = ROOT / f"{slug}.ipynb"
        inject_layman_cell_into_notebook(root_nb, spec, img_prefix=".")

        # 2. Copy notebook and standalone script into the chapter folder, updating relative image path
        ch_nb = ch_dir / f"{slug}.ipynb"
        shutil.copy2(root_nb, ch_nb)
        inject_layman_cell_into_notebook(ch_nb, spec, img_prefix="../..")
        shutil.copy2(ROOT / "scripts" / f"{slug}.py", ch_dir / f"{slug}.py")

        glossary_rows = "\n".join([f"| **{term}** | {desc} |" for term, desc in spec["glossary"]])
        bullets = "\n".join([f"- {h}" for h in spec["highlights"]])
        refs = "\n".join([f"{idx}. {r}" for idx, r in enumerate(spec["references"], start=1)])

        readme_md = f"""# {spec['title']}

{spec['summary']}

---

## 🎨 Visual Concept Overview (Generated with Nano Banana)

![{spec['title']} Concept Visual](../../figures/concepts/{spec['concept_img']})

---

## 🧠 Layman's Guide: {spec['metaphor_title']}

{spec['layman_explanation']}

---

## 🧗 Why This Matters for Agentic Hill-Climbing

> **Role in the Optimization Loop**: **{spec['hill_climbing_role']}**

{spec['hill_climbing_explanation']}

---

## 📖 Plain-English Terminology & Jargon Buster

| Term / Symbol | Plain-English Meaning |
| :--- | :--- |
{glossary_rows}

---

## 📐 Mathematical Formulation (Step-by-Step)

{spec['math']}

---

## ✨ Key Implementation & Simulation Highlights

{bullets}

---

## 📊 Generated Statistical Visualization & How to Read It

![{spec['title']} Statistical Plot](../../figures/{spec['figure']})

### 🔍 How to Read This Chart (Panel-by-Panel)
{spec['chart_walkthrough']}

---

## 🚀 How to Run This Chapter

### 1. Interactive Jupyter Notebook
Open [`{slug}.ipynb`](./{slug}.ipynb) (pre-executed with all outputs, layman guides, and plots embedded) or launch JupyterLab from the repository root:
```bash
uv run jupyter lab chapters/{slug}/{slug}.ipynb
```

### 2. Standalone Python Script
Run the standalone script from the repository root:
```bash
uv run python chapters/{slug}/{slug}.py
```

### 3. Reusable Package Module
Import directly from [`{spec['module']}`](../../{spec['module']}):
```python
import agent_stats
```

---

## 📚 Resources & Reference Material for Deeper Reading

{refs}
"""
        (ch_dir / "README.md").write_text(readme_md, encoding="utf-8")
        print(f"Generated enriched chapters/{slug}/README.md + updated notebooks with Agentic Hill-Climbing sections")


if __name__ == "__main__":
    main()
