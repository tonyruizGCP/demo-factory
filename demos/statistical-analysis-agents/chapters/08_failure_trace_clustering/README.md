# Chapter 8: Failure Trace Mining & Unsupervised Clustering

Parses 300 raw agent failure logs (`stdout`/`stderr`, tool payloads, stack traces), vectorizes them with sublinear TF-IDF, clusters failure modes via PCA + $k$-Means, and synthesizes actionable System Prompt Negative Constraints.

---

## 🎨 Visual Concept Overview (Generated with Nano Banana)

![Chapter 8: Failure Trace Mining & Unsupervised Clustering Concept Visual](../../figures/concepts/ch08_concept.jpg)

---

## 🧠 Layman's Guide: Sorting a Mountain of 300 Crash Receipts into 5 Neat Diagnostic Folders

Imagine your AI agent runs overnight on 1,000 tasks and produces **300 failed crash logs**—each a 40-line wall of messy stack traces, JSON payloads, and error codes.

No human engineer wants to read 300 raw stack traces line by line on Monday morning. Worse, if you just read the first 3 logs, you might think the whole system is failing due to API Timeouts, missing the fact that 60% of the crashes are actually caused by the agent inventing a fake tool parameter!

### How Unsupervised Trace Mining Works
Instead of reading 300 logs manually, we build an automated "Prism" that sorts the pile into distinct root-cause buckets without needing pre-existing labels:
1. **Highlight the Rare Diagnostic Words (`TF-IDF`)**: Every log contains boring boilerplate words like `ERROR`, `Traceback`, `agent_runner.py`. **TF-IDF** automatically mutes words that appear in every log and boosts words that uniquely identify a specific crash (like `429DEADLINE_EXCEEDED`, `maximum_context_length`, or `AdditionalPropertiesError`).
2. **Group into Constellations (`PCA + k-Means`)**: Logs with similar error signatures are pulled into 5 tight geometric clusters.
3. **Pick the Single Best Representative (`Cluster Medoid`)**: Instead of reading 60 logs in Cluster #1, the math finds the single real log sitting closest to the exact center of that cluster (**the Medoid**) and writes a **System Prompt Guardrail** to fix all 60 failures at once!

---

## 📖 Plain-English Terminology & Jargon Buster

| Term / Symbol | Plain-English Meaning |
| :--- | :--- |
| **TF-IDF (Term Frequency–Inverse Document Frequency)** | A text-scoring formula that gives high weight to specific error tokens (like `PermissionError` or `LoopDetectedError`) and near-zero weight to common boilerplate words that appear in every log. |
| **Sublinear TF Scaling ($1 + \log \text{tf}$)** | Prevents a single error word repeated 50 times in a stack-overflow loop from dominating the entire vector. |
| **PCA (Principal Component Analysis)** | A dimensionality-reduction technique that squashes a 500-word vocabulary space down into a 2D map ($x, y$) so we can visualize the clusters on a scatter plot. |
| **$k$-Means Clustering** | An unsupervised algorithm that automatically groups the 300 logs into $k$ neighborhoods based on their cosine/Euclidean similarity. |
| **Silhouette Score** | A quality score from $-1$ to $+1$ measuring how tightly packed each cluster is and how cleanly separated it is from neighboring clusters. The spike at $k=5$ tells us there are exactly 5 failure modes! |
| **Cluster Medoid** | The single actual failure log sits closest to the mathematical center (centroid) of a cluster—the best 'textbook example' for an engineer to inspect. |

---

## 📐 Mathematical Formulation (Step-by-Step)

- **Sublinear TF-IDF Vectorization**:
  For term $t$ in failure log $d$ across $N$ total failure logs:
  $$\text{tfidf}(t, d) = \big(1 + \log \text{tf}(t, d)\big) \cdot \left(\log \frac{1 + N}{1 + \text{df}(t)} + 1\right)$$
- **Cluster Medoid Representative Selection**:
  Finds the real failure log $i \in C_k$ closest to the cluster centroid $\boldsymbol{\mu}_k$:
  $$\text{medoid}(k) = \arg\min_{i \in C_k} \|\mathbf{v}_i - \boldsymbol{\mu}_k\|_2$$

---

## ✨ Key Implementation & Simulation Highlights

- Synthesizes 300 realistic multi-line failure logs across 5 error archetypes: `Tool Schema Hallucination`, `Context Length Exceeded`, `API Timeout`, `Environment Permission Denied`, and `Infinite Loop`.
- Separates all 5 archetypes via unsupervised TF-IDF + $k$-Means (`Adjusted Rand Index = 1.000`, `Silhouette Score = 0.432`).
- Extracts centroid diagnostic keywords, medoid stack traces, and auto-generated **System Prompt Negative Constraints**, exporting both static PNG and interactive Plotly HTML scatter plots.

---

## 📊 Generated Statistical Visualization & How to Read It

![Chapter 8: Failure Trace Mining & Unsupervised Clustering Statistical Plot](../../figures/ch08_failure_trace_clusters.png)

### 🔍 How to Read This Chart (Panel-by-Panel)
- **Left Panel (PCA 2D Projection of 300 Logs)**: Each dot is one raw crash log. Notice how TF-IDF + PCA cleanly separates the 300 messy text logs into **5 distinct islands** (`C0` through `C4`). The black `X` in the center of each island marks its **Medoid**—the single representative trace you need to read.
- **Right Panel (Silhouette Score Model Selection)**: How does an automated pipeline know whether there are 3, 5, or 8 bug types in last night's run? By plotting the **Silhouette Score** across $k=2\dots 8$, the sharp peak at **$k=5$** (`0.432`) automatically discovers the exact number of underlying failure archetypes!

---

## 🚀 How to Run This Chapter

### 1. Interactive Jupyter Notebook
Open [`08_failure_trace_clustering.ipynb`](./08_failure_trace_clustering.ipynb) (pre-executed with all outputs, layman guides, and plots embedded) or launch JupyterLab from the repository root:
```bash
uv run jupyter lab chapters/08_failure_trace_clustering/08_failure_trace_clustering.ipynb
```

### 2. Standalone Python Script
Run the standalone script from the repository root:
```bash
uv run python chapters/08_failure_trace_clustering/08_failure_trace_clustering.py
```

### 3. Reusable Package Module
Import directly from [`agent_stats/ch08_trace_clustering.py`](../../agent_stats/ch08_trace_clustering.py):
```python
import agent_stats
```

---

## 📚 Resources & Reference Material for Deeper Reading

1. **Salton, G., & Buckley, C. (1988).** *Term-weighting approaches in automatic text retrieval.* Information Processing & Management, 24(5), 513–523. — Foundational work on TF-IDF vectorization.
2. **Rousseeuw, P. J. (1987).** *Silhouettes: A graphical aid to the interpretation and validation of cluster analysis.* Journal of Computational and Applied Mathematics, 20, 53–65.
3. **Cemri, M., Pan, M. Z., Yang, S., et al. (2025).** *Why Do Multi-Agent LLM Systems Fail? (MAST Taxonomy).* arXiv:2503.13657. [https://arxiv.org/abs/2503.13657](https://arxiv.org/abs/2503.13657) — Automated trace taxonomy and failure clustering for LLM agent systems.
4. **Manning, C. D., Raghavan, P., & Schütze, H. (2008).** *Introduction to Information Retrieval.* Cambridge University Press. [https://nlp.stanford.edu/IR-book/](https://nlp.stanford.edu/IR-book/)
