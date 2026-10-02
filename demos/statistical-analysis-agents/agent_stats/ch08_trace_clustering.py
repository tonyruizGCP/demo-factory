"""Chapter 8: Failure Trace Mining & Unsupervised Clustering.

Implements:
- Log Synthesizer: generates 300 realistic agent failure logs containing stdout/stderr dumps,
  tool call payloads, and traceback strings across 5 underlying error archetypes:
  1. `Tool Schema Hallucination`
  2. `Context Length Exceeded`
  3. `API Timeout`
  4. `Environment Permission Denied`
  5. `Infinite Loop`
- Vectorization & Feature Extraction using `sklearn.feature_extraction.text.TfidfVectorizer`.
- Dimensionality Reduction (PCA) & Unsupervised Clustering (KMeans + Silhouette & ARI evaluation).
- Auto-Diagnosis & Prompt Mutation Generator:
  * Extracts top TF-IDF diagnostic keywords and medoid representative trace per cluster.
  * Generates structured "Negative Constraints" ready to inject into system prompt optimization loops.
"""

from __future__ import annotations

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.metrics.pairwise import euclidean_distances


ARCHETYPES = [
    "Tool Schema Hallucination",
    "Context Length Exceeded",
    "API Timeout",
    "Environment Permission Denied",
    "Infinite Loop",
]


def generate_synthetic_failure_logs(
    num_logs: int = 300, random_state: int = 42
) -> pd.DataFrame:
    """Generate 300 realistic multi-line agent failure traces across 5 error archetypes."""
    rng = np.random.default_rng(random_state)

    templates = {
        "Tool Schema Hallucination": {
            "tools": ["bigquery_run_sql", "search_codebase", "fetch_customer_record", "update_jira_ticket"],
            "bad_args": ["query_str", "file_glob_pattern", "include_archived_rows", "max_depth_limit"],
            "errors": [
                "pydantic.error_wrappers.ValidationError: 1 validation error for ToolCallPayload\n  Extra inputs are not permitted (type=extra_forbidden)",
                "TypeError: ToolExecutor.invoke() got an unexpected keyword argument '{bad_arg}'",
                "JSONSchemaValidationError: Additional properties are not allowed ('{bad_arg}' was unexpected) in schema tool_call",
            ],
            "stderr": "STDERR: [AgentHarness] Failed to validate tool schema for `{tool}`; hallucinated parameter `{bad_arg}` not in OpenAPI spec.",
        },
        "Context Length Exceeded": {
            "tools": ["read_large_logfile", "dump_database_table", "cat_bundle_js", "fetch_full_repo_tree"],
            "bad_args": ["limit=None", "raw_dump=True", "max_bytes=10000000"],
            "errors": [
                "google.api_core.exceptions.InvalidArgument: 400 The input token count (1,148,592) exceeds the maximum number of tokens allowed (1,048,576).",
                "ContextWindowExceededError: Prompt length 264,190 tokens exceeds configured model context_limit=200,000.",
                "RuntimeError: Token budget exhausted during tool_response serialization (untruncated stdout payload: 4.8 MB).",
            ],
            "stderr": "STDERR: [ContextManager] Fatal overflow appending `{tool}` output ({bad_arg}) to conversation trajectory.",
        },
        "API Timeout": {
            "tools": ["vertex_batch_predict", "external_rest_webhook", "snowflake_warehouse_query", "remote_rpc_call"],
            "bad_args": ["timeout_ms=60000", "retry_backoff=2.0", "endpoint='us-central1'"],
            "errors": [
                "httpx.ReadTimeout: timed out waiting for response bytes from upstream gateway after 60.0s",
                "grpc._channel._InactiveRpcError: StatusCode.DEADLINE_EXCEEDED: Deadline Exceeded waiting for backend service",
                "requests.exceptions.ConnectTimeout: HTTPSConnectionPool(host='api.partner-service.io', port=443): Read timed out.",
            ],
            "stderr": "STDERR: [ToolRunner] Upstream RPC deadline exceeded while executing `{tool}` ({bad_arg}); socket closed after 3 retries.",
        },
        "Environment Permission Denied": {
            "tools": ["bash_exec", "write_system_file", "gcs_upload_artifact", "iam_set_policy"],
            "bad_args": ["path='/etc/sudoers.d/agent'", "bucket='prod-restricted-vault'", "mode='0777'"],
            "errors": [
                "PermissionError: [Errno 13] Permission denied: '/etc/shadow' during sandboxed tool execution",
                "google.api_core.exceptions.PermissionDenied: 403 Caller does not have storage.objects.create access to the Google Cloud Storage bucket.",
                "subprocess.CalledProcessError: Command 'chmod +x /usr/local/bin/deploy.sh' returned exit status 126: Operation not permitted in sandbox.",
            ],
            "stderr": "STDERR: [SandboxGuard] Security policy violation or OS EACCES blocked `{tool}` on resource ({bad_arg}).",
        },
        "Infinite Loop": {
            "tools": ["list_directory", "check_task_status", "grep_search", "think_step"],
            "bad_args": ["dir='.'", "poll_id='job-991'", "pattern='TODO'"],
            "errors": [
                "MaxIterationsExceededError: Agent reached maximum step limit (max_steps=50) repeating identical tool call `{tool}({bad_arg})` 18 times.",
                "TrajectoryCycleDetectedError: Cyclic state transition detected over last 12 turns without state mutation or new observation.",
                "RecursionError: Agent planner stuck in repetitive retry loop calling `{tool}` with identical arguments.",
            ],
            "stderr": "STDERR: [LoopDetector] Aborting run after 15 consecutive identical invocations of `{tool}` ({bad_arg}).",
        },
    }

    noise_phrases = [
        "INFO: trace_id=0x9f8a2b session_env=linux_x86_64container",
        "DEBUG: latency_ms=412.3 memory_rss_mb=518.4",
        "WARN: telemetry flush queued for span_id=ab1902",
        "INFO: model_checkpoint=gemini-3-flash-preview temperature=0.2",
    ]

    rows = []
    per_arch = num_logs // len(ARCHETYPES)
    for arch_idx, arch in enumerate(ARCHETYPES):
        spec = templates[arch]
        count = per_arch if arch_idx < len(ARCHETYPES) - 1 else num_logs - len(rows)
        for i in range(count):
            tool = str(rng.choice(spec["tools"]))
            bad_arg = str(rng.choice(spec["bad_args"]))
            err_tmpl = str(rng.choice(spec["errors"]))
            err_str = err_tmpl.format(tool=tool, bad_arg=bad_arg)
            stderr_str = spec["stderr"].format(tool=tool, bad_arg=bad_arg)
            noise = str(rng.choice(noise_phrases))

            raw_log = (
                f"{noise}\n"
                f"TOOL_CALL: {tool}({bad_arg})\n"
                f"{stderr_str}\n"
                f"TRACEBACK: {err_str}"
            )
            rows.append(
                {
                    "log_id": f"FAIL-{len(rows) + 1:03d}",
                    "true_archetype": arch,
                    "tool_name": tool,
                    "raw_trace": raw_log,
                }
            )

    df = pd.DataFrame(rows)
    return df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)


def cluster_and_diagnose_traces(
    df_logs: pd.DataFrame, n_clusters: int = 5, random_state: int = 42
) -> Dict[str, object]:
    """Vectorize failure logs with TF-IDF, reduce with PCA, cluster with K-Means, and generate prompt constraints."""
    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(df_logs["raw_trace"])
    feature_names = vectorizer.get_feature_names_out()

    # Dimensionality reduction to 2D via PCA for visualization
    pca = PCA(n_components=2, random_state=random_state)
    coords_2d = pca.fit_transform(tfidf_matrix.toarray())

    # K-Means clustering
    kmeans = KMeans(n_clusters=n_clusters, n_init=20, random_state=random_state)
    cluster_ids = kmeans.fit_predict(tfidf_matrix)

    sil_score = float(silhouette_score(tfidf_matrix, cluster_ids))
    ari_score = float(adjusted_rand_score(df_logs["true_archetype"], cluster_ids))

    df_out = df_logs.copy()
    df_out["cluster_id"] = cluster_ids
    df_out["pca_x"] = coords_2d[:, 0]
    df_out["pca_y"] = coords_2d[:, 1]

    # Extract top TF-IDF terms, medoid trace, and auto-generated Negative Constraint per cluster
    cluster_summaries = []
    dense_mat = tfidf_matrix.toarray()

    for cid in range(n_clusters):
        mask = cluster_ids == cid
        cluster_indices = np.where(mask)[0]
        centroid = kmeans.cluster_centers_[cid]

        top_term_idx = np.argsort(centroid)[::-1][:6]
        top_terms = [str(feature_names[idx]) for idx in top_term_idx]

        # Find medoid (closest actual log trace to cluster centroid)
        dists = euclidean_distances(dense_mat[mask], centroid.reshape(1, -1)).ravel()
        medoid_global_idx = int(cluster_indices[int(np.argmin(dists))])
        medoid_trace = str(df_out.loc[medoid_global_idx, "raw_trace"])
        dominant_archetype = str(
            df_out.loc[mask, "true_archetype"].mode().iloc[0]
        )

        negative_constraint = generate_negative_constraint(top_terms, medoid_trace)

        cluster_summaries.append(
            {
                "cluster_id": cid,
                "count": int(np.sum(mask)),
                "dominant_archetype": dominant_archetype,
                "top_keywords": ", ".join(top_terms),
                "medoid_log_id": str(df_out.loc[medoid_global_idx, "log_id"]),
                "medoid_snippet": medoid_trace.splitlines()[-1][:110],
                "negative_constraint": negative_constraint,
            }
        )

    summary_df = pd.DataFrame(cluster_summaries)
    label_map = {
        row["cluster_id"]: f"Cluster {row['cluster_id']}: {row['top_keywords'].split(',')[0]}"
        for _, row in summary_df.iterrows()
    }
    df_out["cluster_label"] = df_out["cluster_id"].map(label_map)

    return {
        "logs_df": df_out,
        "summary_df": summary_df,
        "silhouette_score": sil_score,
        "adjusted_rand_index": ari_score,
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
    }


def generate_negative_constraint(top_terms: List[str], medoid_trace: str) -> str:
    """Convert cluster keywords and medoid trace into an actionable system prompt Negative Constraint."""
    joined = " ".join(top_terms).lower() + " " + medoid_trace.lower()
    if "schema" in joined or "extra_forbidden" in joined or "keyword argument" in joined:
        return (
            "NEVER invent or pass undocumented tool arguments; strictly validate all tool "
            "parameters against the declared JSON Schema before invoking any tool."
        )
    if "token" in joined or "context" in joined or "overflow" in joined:
        return (
            "NEVER dump unbounded files or raw tables into context; ALWAYS pass pagination/line "
            "limits (`head`, `limit=50`) to keep tool outputs under 8,000 tokens."
        )
    if "timeout" in joined or "deadline_exceeded" in joined or "timed" in joined:
        return (
            "DO NOT issue synchronous blocking calls without a timeout fallback; on DEADLINE_EXCEEDED, "
            "narrow query scope or switch to async polling instead of blind retries."
        )
    if "permission" in joined or "403" in joined or "eacces" in joined:
        return (
            "NEVER attempt privileged writes outside the workspace sandbox (`/etc`, restricted GCS buckets); "
            "verify IAM/filesystem permissions and write only to approved user directories."
        )
    return (
        "NEVER invoke the same tool with identical arguments more than 2 times consecutively; "
        "if state does not advance, halt and reformulate your plan."
    )
