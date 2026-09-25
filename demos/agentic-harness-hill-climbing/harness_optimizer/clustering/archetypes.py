import numpy as np
from typing import List, Sequence, Optional, Any
from dataclasses import dataclass

@dataclass
class ArchetypeCluster:
    cluster_id: int
    size: int
    exemplars: List[str]
    top_terms: List[str]
    members: List[str]

    @property
    def diagnostic_terms(self):
        return self.top_terms

    @property
    def exemplar(self):
        return self.exemplars[0] if self.exemplars else None

    @property
    def representative_trace(self):
        return self.exemplar

class ClusteredFailureReport:
    def __init__(self, clusters: List[ArchetypeCluster], n_clusters: int, labels: List[int]):
        self.clusters = clusters
        self.n_clusters = n_clusters
        self.labels = labels
        
    def __len__(self):
        return len(self.clusters)
        
    def __getitem__(self, idx):
        return self.clusters[idx]
        
    def __iter__(self):
        return iter(self.clusters)

class ArchetypeClusterer:
    def __init__(self, k_clusters: int = 3, max_iter: int = 100, random_state: Optional[int] = None):
        self.k_clusters = k_clusters
        self.max_iter = max_iter
        self.random_state = random_state

    def fit_predict(self, X: Any, traces: Optional[Sequence[str]] = None) -> ClusteredFailureReport:
        feature_names = []
        if traces is None and isinstance(X, (list, tuple)):
            traces = X
            from harness_optimizer.clustering.vectorizer import TraceVectorizer
            vec = TraceVectorizer(ngram_range=(1, 2))
            X = vec.fit_transform(traces)
            feature_names = vec.get_feature_names()
            
        N = len(X)
        if N == 0:
            return ClusteredFailureReport([], 0, [])
            
        V = X.shape[1] if len(X.shape) > 1 else 0
        
        row_norms = np.linalg.norm(X, axis=1, keepdims=True)
        X_norm = np.divide(X, row_norms, out=np.zeros_like(X), where=row_norms!=0)
        
        effective_k = min(self.k_clusters, max(1, N))
        
        rng = np.random.RandomState(self.random_state if self.random_state is not None else 42)
        
        C = np.zeros((effective_k, V), dtype=np.float64)
        if effective_k > 0 and V > 0:
            first_idx = rng.randint(N)
            C[0] = X_norm[first_idx]
            for i in range(1, effective_k):
                sims = X_norm @ C[:i].T
                max_sims = np.max(sims, axis=1)
                dists = 1.0 - max_sims
                dists = np.maximum(dists, 0.0)
                if np.sum(dists) > 0:
                    probs = dists / np.sum(dists)
                    next_idx = rng.choice(N, p=probs)
                else:
                    next_idx = rng.randint(N)
                C[i] = X_norm[next_idx]
        
        labels = np.zeros(N, dtype=int)
        for _ in range(self.max_iter):
            if V == 0:
                labels = np.zeros(N, dtype=int)
                break
                
            S = X_norm @ C.T
            new_labels = np.argmax(S, axis=1)
            if np.array_equal(labels, new_labels):
                break
            labels = new_labels
            
            for j in range(effective_k):
                members_mask = (labels == j)
                if np.any(members_mask):
                    cluster_pts = X_norm[members_mask]
                    sum_vec = np.sum(cluster_pts, axis=0)
                    norm = np.linalg.norm(sum_vec)
                    if norm > 0:
                        C[j] = sum_vec / norm
                    else:
                        C[j] = sum_vec
                else:
                    rand_idx = rng.randint(N)
                    C[j] = X_norm[rand_idx]
                    
        clusters = []
        for j in range(effective_k):
            members_idx = np.where(labels == j)[0]
            members = [traces[i] for i in members_idx] if traces else []
            size = len(members_idx)
            
            exemplars = []
            if size > 0 and V > 0 and traces:
                cluster_X = X_norm[members_idx]
                sims = cluster_X @ C[j]
                best_idx_in_cluster = np.argmax(sims)
                exemplars = [traces[members_idx[best_idx_in_cluster]]]
            elif size > 0 and traces:
                exemplars = [traces[members_idx[0]]]
                
            top_terms = []
            if V > 0 and feature_names:
                top_indices = np.argsort(C[j])[::-1][:5]
                top_terms = [feature_names[idx] for idx in top_indices if C[j, idx] > 0]

            if not top_terms and members:
                import re
                from collections import Counter
                words = []
                for m in members:
                    words.extend(re.findall(r'[A-Za-z0-9_]{3,}', str(m)))
                if words:
                    counts = Counter(words)
                    top_terms = [w for w, _ in counts.most_common(5)]
                else:
                    for m in members:
                        words.extend(re.findall(r'\S+', str(m)))
                    if words:
                        counts = Counter(words)
                        top_terms = [w for w, _ in counts.most_common(5)]
            if not top_terms:
                top_terms = ["error"]
                
            clusters.append(ArchetypeCluster(
                cluster_id=j,
                size=size,
                exemplars=exemplars,
                top_terms=top_terms,
                members=members
            ))
            
        return ClusteredFailureReport(clusters, effective_k, labels.tolist())

    def cluster(self, traces: List[str]) -> ClusteredFailureReport:
        return self.fit_predict(traces)

    def cluster_telemetry(self, telemetry_list: List[Any]) -> ClusteredFailureReport:
        traces = []
        for t in telemetry_list:
            if hasattr(t, "raw_error_message"):
                traces.append(str(t.raw_error_message))
            else:
                traces.append(str(t))
        return self.fit_predict(traces)
