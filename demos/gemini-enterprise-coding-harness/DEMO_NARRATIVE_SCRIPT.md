# Customer CE Demo Guide: The 3-Act Hill-Climbing Narrative

> **Audience**: CTOs, VPs of Engineering, Lead AI Architects, and Platform Teams  
> **Presenter**: Tony Ruiz | Specialist Customer Engineer, Google Cloud Enterprise AI  
> **Central Thesis**: $\text{Agent} = \text{Model} + \text{Harness}$. When an agent struggles, don't swap or fine-tune models—**hill-climb the harness**.

---

## Executive Narrative Overview

| Act | Theme | Customer Pain / Revelation | Live Demo Action |
| :--- | :--- | :--- | :--- |
| **Act 1** | **The Baseline Struggle** *(The 80% Chasm)* | "Our prompt-based coding agent pilot is stuck at 35% pass rate and burns tokens on broken code." | Run baseline harness on 8 enterprise tasks: watch it stumble on AST syntax errors, token limits, and guideline violations (37.5% pass rate). |
| **Act 2** | **Autonomous Hill-Climbing** *(The Engine)* | "Tuning prompts manually takes weeks, and sweeping blindly burns thousands of dollars." | Launch `run_narrative_demo.py`: Bayesian sequential early stopping prunes bad candidates in 3 steps (saving 62.5% compute); trace miner clusters root errors. |
| **Act 3** | **Re-Evaluation & Victory** *(The Generalization)* | "How do I know this isn't just overfitting to a test suite?" | Candidate B evaluated: early acceptance at Step 7 ($P \ge 0.95$); quarantined McNemar holdout test passes ($p < 0.05$). Pass rate jumps to 87.5%! |

---

## Fast Start: Executing the Live Demo

Run directly in your terminal in front of the customer:

```bash
cd /usr/local/google/home/tonyruiz/Desktop/demos/jetski/demos/demo-factory/demos/gemini-enterprise-coding-harness

# Dynamic presentation mode (with realistic visual pacing)
python3 run_narrative_demo.py

# Or lightning speed (for quick dry-runs)
python3 run_narrative_demo.py --fast
```

---

## Presenter Talk Track & Stage Directions

### Act 1: The Baseline Struggle (The 80% Chasm)

#### 🎙️ Presenter Script:
> *"Thanks everyone for having us today. Over the past 18 months, almost every engineering leadership team I meet has run a coding agent pilot. And over 80% of them are currently stalled.*
>
> *Why? Because frontier models like Gemini are brilliant reasoning engines, but they are not an operating system. A raw model without a structured harness doesn't know your repository rules, tries to dump entire files into context, writes partial code patches that corrupt AST syntax, and commits broken code.*
>
> *Let’s look at what happens when a standard baseline agent tackles 8 realistic enterprise tasks in your codebase."*

#### 🖥️ Action on Screen:
Run `python3 run_narrative_demo.py`.
The terminal displays the baseline run over the optimization suite:
```text
  Task 01/08 ge_task_01_async_refactor          -> [FAIL] (SyntaxError in async patch)
  Task 02/08 ge_task_02_lsp_symbol_lookup       -> [PASS]
  Task 03/08 ge_task_03_prewalk_guidelines      -> [FAIL] (GuidelineViolation: connection leak)
  Task 04/08 ge_task_04_semantic_patch_guard    -> [FAIL] (ASTSyntaxError: corrupt function header)
  Task 05/08 ge_task_05_worktree_isolation      -> [PASS]
  Task 06/08 ge_task_06_dap_test_runner         -> [FAIL] (Pytest exit code 1)
  Task 07/08 ge_task_07_memory_consolidation    -> [FAIL] (ContextWindowExceeded: blew 32k tokens)
  Task 08/08 ge_task_08_multi_turn_rewind       -> [PASS]

  Baseline Score: 3/8 (37.5% pass rate) | Avg Token Spend: 3,840 tokens
```

#### 🎙️ Presenter Script:
> *"Look at this scoreboard: a 37.5% pass rate. Would you ever allow an agent with a 37% pass rate to push code to your trunk? Of course not.*
>
> *Notice what failed:*
> 1. *It failed on AST syntax because it tried to do string replacements instead of AST-aware patching.*
> 2. *It blew past token limits because it dumped whole files instead of querying symbols via Language Server Protocol (LSP).*
> 3. *It violated enterprise guidelines because it wasn't grounded in corporate memory.*
>
> *Now, the traditional industry reflex is: 'Let’s spend $80,000 fine-tuning a custom 70B model or spend three weeks tweaking prompt adjectives.' We believe that’s the wrong answer."*

---

### Act 2: Autonomous Hill-Climbing in Action

#### 🎙️ Presenter Script:
> *"Here is Google Cloud's thesis: **Agent = Model + Harness**.*
>
> *Instead of manually guessing what went wrong, we connect our Autonomous Evaluation & Hill-Climbing Harness. It does three things that human developers cannot do at scale:*
> 1. *It partitions your task suite into an active optimization set and a cryptographically quarantined holdout vault.*
> 2. *It uses **Bayesian Sequential Early Stopping** to kill bad ideas immediately without burning your budget.*
> 3. *It uses **Unsupervised Trace Mining** to cluster stack traces and tell us exactly what architectural tool is missing.*
>
> *Watch what happens when we test Candidate A—a naive prompt trying to force strict JSON."*

#### 🖥️ Action on Screen:
The terminal executes Candidate A:
```text
  Step 1/8 [ge_task_01_async_refactor]: Passed=False | P(cand > base)=0.2222 -> CONTINUE
  Step 2/8 [ge_task_02_lsp_symbol_lookup]: Passed=False | P(cand > base)=0.1212 -> CONTINUE
  Step 3/8 [ge_task_03_prewalk_guidelines]: Passed=False | P(cand > base)=0.0707 -> PRUNE

  >> BAYESIAN SEQUENTIAL EARLY PRUNING TRIGGERED!
  • Decision: PRUNE (P = 0.0707 <= 0.10 threshold)
  • Compute Efficiency: Terminated after 3 evaluations! Saved 5 trials (62.5% budget saved)
```

#### 🎙️ Presenter Script:
> *"Did you see that? At Step 3, our Beta-Binomial Bayesian engine calculated that the probability of Candidate A being superior to baseline dropped to 7.07%. Because that’s below our 10% threshold, it pruned the candidate immediately!*
>
> *A standard test suite would have run all 8 tasks and burned 40,000 tokens. Our hill-climber cut it off in 3 steps, saving 62.5% of the evaluation budget.*
>
> *Next, our trace miner clusters the real error logs:"*

```text
  • Archetype #0: 'SyntaxError: invalid syntax in async patch hunk'
  • Archetype #1: 'ContextWindowExceeded: uncompressed session state'
```

#### 🎙️ Presenter Script:
> *"The data reveals the truth: the failure wasn't the model's intelligence—it was a missing AST validation hook and missing memory grounding. The hill-climber automatically synthesizes the fix into Candidate B:*
> - *Added In-Process AST Syntax Verification Hook.*
> - *Injected Vertex AI Memory Bank guidelines into the prewalk callback.*
> - *Enabled LSP symbol scoping to replace raw file reads."*

---

### Act 3: Re-Evaluation & Proven Generalization

#### 🎙️ Presenter Script:
> *"Now let's re-run Candidate B with the hardened enterprise harness."*

#### 🖥️ Action on Screen:
The terminal executes Candidate B:
```text
  Step 1/8 [ge_task_01_async_refactor]: Passed=True | P(cand > base)=0.6667 -> CONTINUE
  Step 2/8 [ge_task_02_lsp_symbol_lookup]: Passed=True | P(cand > base)=0.7879 -> CONTINUE
  Step 3/8 [ge_task_03_prewalk_guidelines]: Passed=True | P(cand > base)=0.8586 -> CONTINUE
  Step 4/8 [ge_task_04_semantic_patch_guard]: Passed=True | P(cand > base)=0.9021 -> CONTINUE
  Step 5/8 [ge_task_05_worktree_isolation]: Passed=True | P(cand > base)=0.9301 -> CONTINUE
  Step 6/8 [ge_task_06_dap_test_runner]: Passed=True | P(cand > base)=0.9487 -> CONTINUE
  Step 7/8 [ge_task_07_memory_consolidation]: Passed=True | P(cand > base)=0.9615 -> ACCEPT

  >> BAYESIAN EARLY ACCEPTANCE TRIGGERED at Step 7!
  • Posterior Superiority: P(cand > base) = 0.9615 >= 0.95 threshold
```

#### 🎙️ Presenter Script:
> *"By Step 7, posterior superiority crossed 96.1%, triggering early acceptance.*
>
> *Now comes the most critical engineering gate: **The Quarantined Holdout Gate**. In machine learning, Goodhart's law warns that any metric targeted becomes a bad metric. How do we know Candidate B didn't just overfit to our prompt?*
>
> *The system evaluates Candidate B on quarantined tasks that neither the prompt nor the agent has ever seen, using a paired McNemar test with exact binomial scoring."*

```text
  • Holdout Tasks Evaluated:  8 tasks (Quarantined, zero prompt leakage)
  • Baseline Holdout Pass:    2/8 (25.0%)
  • Candidate B Holdout Pass: 8/8 (100.0%)
  • McNemar Exact p-value:    p = 0.0312 (Statistically Significant < 0.05)
  • Gate Verdict:             PROMOTION APPROVED! GENERALIZATION VERIFIED.
```

#### 🖥️ Final Scoreboard Display:
```text
┌─────────────────────────────────────┬──────────────────┬──────────────────┬───────────────┐
│ Key Engineering Metric              │ Baseline Harness │ Tuned Harness    │ Delta / Impact│
├─────────────────────────────────────┼──────────────────┼──────────────────┼───────────────┤
│ Enterprise Pass Rate                │ 37.5% (3/8)      │ 87.5% (7/8)      │ +50.0% Gain   │
│ AST Syntax Patch Failures           │ 3 instances      │ 0 instances      │ -100% (Zeroed)│
│ Avg Context Token Spend / Task      │ 3,840 tokens     │ 1,420 tokens     │ -63.0% Cost   │
│ Bad Candidate Pruning Speed         │ N/A (Manual)     │ 3 Steps (0.05s)  │ 62.5% Savings │
│ Holdout Generalization Verified     │ Failed           │ Passed (p=0.031) │ CI/CD Ready   │
└─────────────────────────────────────┴──────────────────┴──────────────────┴───────────────┘
```

#### 🎙️ Concluding Talk Track:
> *"Here is the bottom line for your platform team:*
> - *We increased task pass rate from 37.5% to 87.5% (+50% gain).*
> - *We eradicated 100% of AST syntax corruptions.*
> - *We slashed token consumption by 63% by using LSP symbol navigation instead of brute-force context stuffing.*
> - *And we proved with mathematical certainty ($p = 0.0312$) that this generalizes to unseen tasks.*
>
> *You don't need a new foundation model. You need the Gemini Enterprise Coding Harness backed by our Autonomous Hill-Climbing engine. Let's schedule a 1-day architecture workshop to connect your Git repositories."*

---

## Executive Q&A / Objection Handling

### Q1: *"Can we run this on our own internal benchmarks instead of synthetic tasks?"*
> **Answer**: *"Absolutely. BenchHub ingests standard ATIF (Agent Task Interchange Format) YAML/JSON files. You point it to your internal GitHub/GitLab PRs or test repositories, and the stratified splitter will automatically partition them into optimization and holdout sets with zero data leakage."*

### Q2: *"Why Bayesian early stopping instead of running every benchmark test to completion?"*
> **Answer**: *"Cost and velocity. Running 100 enterprise agent trials on Gemini 3.8 Flash or Pro can cost dozens of dollars and take 15 minutes per candidate. When a candidate mutation is clearly failing, running it to completion is burning compute for zero information gain. Our Beta-Binomial conjugate engine detects failure in 3 to 5 trials with mathematical confidence, saving 60%+ in test budget."*

### Q3: *"How does this prevent prompt engineers from gaming the benchmarks?"*
> **Answer**: *"The paired McNemar Holdout Gate. Promising candidates are quarantined and evaluated on a holdout partition that is never exposed during optimization. Unless the candidate demonstrates statistically significant improvements ($p < 0.05$) on unseen tasks, the state machine forcibly rejects it and dumps it back into trace diagnosis."*
