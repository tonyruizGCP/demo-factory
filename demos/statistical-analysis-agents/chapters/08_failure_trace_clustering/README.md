# Chapter 8: Failure Trace Mining & Unsupervised Clustering

Parses 300 raw agent failure logs (`stdout`/`stderr`, tool payloads, stack traces), vectorizes them with sublinear TF-IDF, clusters failure modes via PCA + $k$-Means, and synthesizes actionable System Prompt Negative Constraints.

---

## 📐 Mathematical Formulation

- **Sublinear TF-IDF Vectorization**:
  $$\text{tfidf}(t, d) = (1 + \log \text{tf}(t, d)) \cdot \left(\log \frac{1 + N}{1 + \text{df}(t)} + 1\right)$$
- **Cluster Medoid Trace Selection**:
  $$\text{medoid}(k) = \arg\min_{i \in C_k} \|\mathbf{v}_i - \boldsymbol{\mu}_k\|_2$$

---

## ✨ Key Implementation Highlights

- Synthesizes 300 realistic multi-line failure logs across 5 error archetypes: `Tool Schema Hallucination`, `Context Length Exceeded`, `API Timeout`, `Environment Permission Denied`, and `Infinite Loop`.
- Separates all 5 archetypes via unsupervised TF-IDF + $k$-Means (`Adjusted Rand Index = 1.000`, `Silhouette Score = 0.432`).
- Extracts centroid diagnostic keywords, medoid stack traces, and auto-generated **System Prompt Negative Constraints**, exporting both static PNG and interactive Plotly HTML scatter plots.

---

## 📊 Generated Visualization

![Chapter 8: Failure Trace Mining & Unsupervised Clustering](../../figures/ch08_failure_trace_clusters.png)

---

## 🚀 How to Run This Chapter

### 1. Interactive Jupyter Notebook
Open [`08_failure_trace_clustering.ipynb`](./08_failure_trace_clustering.ipynb) (pre-executed with all outputs and plots embedded) or launch JupyterLab from the repository root:
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
