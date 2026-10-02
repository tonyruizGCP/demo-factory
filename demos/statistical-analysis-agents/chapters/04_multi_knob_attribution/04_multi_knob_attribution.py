"""Standalone runnable script for 04_multi_knob_attribution."""
import matplotlib
matplotlib.use('Agg')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from agent_stats.ch04_multi_knob_regression import (
    extract_developer_insights,
    fit_response_surface_model,
    generate_multi_knob_dataset,
)

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 120

df_knobs = generate_multi_knob_dataset(n_samples=300, random_state=42)
model = fit_response_surface_model(df_knobs)
print(model.summary())

insights = extract_developer_insights(model)
opt_t = insights["optimal_thinking_budget"]
opt_c = insights["optimal_context_chunks"]

t_grid = np.linspace(100, 4000, 60)
c_grid = np.linspace(1, 20, 60)
tt, cc = np.meshgrid(t_grid, c_grid)
grid_df = pd.DataFrame({
    "thinking_budget": tt.ravel(),
    "context_chunks": cc.ravel(),
    "tool_timeout": np.full(tt.size, 30.0),
})
zz = model.predict(grid_df).to_numpy().reshape(tt.shape)

fig = plt.figure(figsize=(15, 6.0))

# Subplot 1: 3D Response Surface
ax1 = fig.add_subplot(1, 2, 1, projection="3d")
surf = ax1.plot_surface(tt, cc, zz, cmap="viridis", alpha=0.88, edgecolor="none")
ax1.scatter([opt_t], [opt_c], [ np.max(zz) ], color="red", s=80, label="Global Optimum")
ax1.set_title("3D Response Surface: Pass Rate vs. Thinking & Context", fontsize=11.5, fontweight="bold")
ax1.set_xlabel("Thinking Budget (Tokens)")
ax1.set_ylabel("Context Chunks (k)")
ax1.set_zlabel("Predicted Pass Rate")
ax1.view_init(elev=28, azim=-125)

# Subplot 2: 2D Contour Map with Stationary Optimum & Overthinking Zone
ax2 = fig.add_subplot(1, 2, 2)
cntr = ax2.contourf(tt, cc, zz, levels=18, cmap="viridis")
cs = ax2.contour(tt, cc, zz, levels=10, colors="white", linewidths=0.8, alpha=0.7)
ax2.clabel(cs, inline=True, fontsize=8, fmt="%.2f")
plt.colorbar(cntr, ax=ax2, label="Predicted Pass Rate")

ax2.scatter([opt_t], [opt_c], color="#ff2a2a", edgecolor="white", s=140, zorder=5, marker="*", label=f"Stationary Optimum ({opt_t:,.0f} tok, {opt_c:.1f} chunks)")
ax2.axvline(opt_t, color="white", linestyle="--", alpha=0.7)
ax2.axhline(opt_c, color="white", linestyle="--", alpha=0.7)
ax2.set_title("2D Contour Map & Optimal Parameter Region (timeout=30s)", fontsize=11.5, fontweight="bold")
ax2.set_xlabel("Thinking Budget (Tokens)")
ax2.set_ylabel("Context Chunks Retrieved")
ax2.legend(loc="lower right", facecolor="#222222", labelcolor="white", framealpha=0.85)

plt.tight_layout()
plt.savefig("figures/ch04_multi_knob_response_surface.png", dpi=150, bbox_inches="tight")
plt.show()

print("=== AUTOMATED DEVELOPER REGRESSION INSIGHTS ===")
for line in insights["plain_english_insights"]:
    print(line)
