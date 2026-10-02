"""Standalone runnable script for 08_failure_trace_clustering."""
import matplotlib
matplotlib.use('Agg')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from agent_stats.ch08_trace_clustering import (
    cluster_and_diagnose_traces,
    generate_synthetic_failure_logs,
)

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 120

df_logs = generate_synthetic_failure_logs(num_logs=300, random_state=42)
res = cluster_and_diagnose_traces(df_logs, n_clusters=5, random_state=42)

print(f"Synthesized {len(df_logs)} agent failure traces across 5 underlying archetypes.")
print(f"Unsupervised Clustering Quality -> Silhouette Score: {res['silhouette_score']:.3f} | Adjusted Rand Index (vs ground truth): {res['adjusted_rand_index']:.3f}")

res["summary_df"][["cluster_id", "count", "dominant_archetype", "top_keywords", "medoid_log_id"]]

print("=== AUTO-GENERATED SYSTEM PROMPT NEGATIVE CONSTRAINTS ===")
for _, row in res["summary_df"].iterrows():
    print(f"[Cluster {row['cluster_id']} | {row['dominant_archetype']} (n={row['count']})]")
    print(f"  Top TF-IDF Keywords : {row['top_keywords']}")
    print(f"  Medoid Trace ({row['medoid_log_id']}): {row['medoid_snippet']}")
    print(f"  -> Prompt Constraint: {row['negative_constraint']}")
    print("-" * 95)

import plotly.express as px

logs_df = res["logs_df"]
summary_df = res["summary_df"]

# 1. Static High-DPI Scatter Plot with Centroid Diagnostic Labels
fig, ax = plt.subplots(figsize=(11.5, 6.2))
sns.scatterplot(
    data=logs_df,
    x="pca_x",
    y="pca_y",
    hue="cluster_label",
    style="true_archetype",
    s=75,
    alpha=0.85,
    palette="tab10",
    ax=ax,
)

for _, row in summary_df.iterrows():
    cid = row["cluster_id"]
    sub = logs_df[logs_df["cluster_id"] == cid]
    cx, cy = sub["pca_x"].mean(), sub["pca_y"].mean()
    ax.text(
        cx, cy + 0.04,
        f"Cluster {cid}: {row['dominant_archetype']}\n({row['top_keywords'].split(',')[0]})",
        ha="center", va="bottom", fontsize=8.5, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#333333", alpha=0.9),
    )

ax.set_title("2D PCA Projection of 300 Clustered Agent Failure Traces (TF-IDF + K-Means)", fontsize=12.5, fontweight="bold")
ax.set_xlabel(f"PCA Component 1 ({res['explained_variance_ratio'][0]:.1%} variance)")
ax.set_ylabel(f"PCA Component 2 ({res['explained_variance_ratio'][1]:.1%} variance)")
ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8.5)

plt.tight_layout()
plt.savefig("figures/ch08_failure_trace_clusters.png", dpi=150, bbox_inches="tight")
plt.show()

# 2. Save Interactive Plotly HTML Scatter Plot
fig_plotly = px.scatter(
    logs_df,
    x="pca_x",
    y="pca_y",
    color="cluster_label",
    symbol="true_archetype",
    hover_data=["log_id", "tool_name", "true_archetype"],
    title="Interactive 2D Clustered Agent Failure Traces (Chapter 8)",
)
fig_plotly.write_html("figures/ch08_interactive_failure_clusters.html")
print("Saved interactive Plotly scatter plot to figures/ch08_interactive_failure_clusters.html")
