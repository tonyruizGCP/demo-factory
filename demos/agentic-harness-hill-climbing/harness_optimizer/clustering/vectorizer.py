import re
import math
from collections import defaultdict, Counter
from typing import Sequence, Tuple, Optional, List, Dict
import numpy as np

class TraceVectorizer:
    def __init__(self, ngram_range: Tuple[int, int] = (1, 1), max_features: Optional[int] = None, 
                 force_numpy: bool = False, min_df: int = 1, sublinear_tf: bool = True):
        self.ngram_range = ngram_range
        self.max_features = max_features
        self.force_numpy = force_numpy
        self.min_df = min_df
        self.sublinear_tf = sublinear_tf
        self.vocabulary_: Dict[str, int] = {}
        self.feature_names_: List[str] = []
        self.idf_: np.ndarray = np.array([])
        
        self.stop_words = {'and', 'the', 'is', 'in', 'at', 'of', 'for', 'with', 'to', 'a', 'an'}
        self.token_pattern = re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b')

    def _tokenize(self, text: str) -> List[str]:
        text = str(text).lower()
        tokens = self.token_pattern.findall(text)
        return [t for t in tokens if t not in self.stop_words]

    def _get_ngrams(self, tokens: List[str]) -> List[str]:
        ngrams = []
        min_n, max_n = self.ngram_range
        for n in range(min_n, max_n + 1):
            for i in range(len(tokens) - n + 1):
                ngrams.append(" ".join(tokens[i:i+n]))
        return ngrams

    def fit(self, documents: Sequence[str]):
        df_counts = Counter()
        doc_count = len(documents)
        
        for doc in documents:
            tokens = self._tokenize(doc)
            ngrams = self._get_ngrams(tokens)
            unique_ngrams = set(ngrams)
            for ngram in unique_ngrams:
                df_counts[ngram] += 1
                
        filtered_items = [(term, df) for term, df in df_counts.items() if df >= self.min_df]
        
        # Sort for max_features (DF descending, then alphabetical)
        filtered_items.sort(key=lambda x: (-x[1], x[0]))
        
        if self.max_features is not None:
            filtered_items = filtered_items[:self.max_features]
            
        self.feature_names_ = [item[0] for item in filtered_items]
        self.vocabulary_ = {term: idx for idx, term in enumerate(self.feature_names_)}
        
        idf_list = []
        for term, df in filtered_items:
            idf = math.log((1 + doc_count) / (1 + df)) + 1.0
            idf_list.append(idf)
            
        self.idf_ = np.array(idf_list, dtype=np.float64)
        return self

    def transform(self, documents: Sequence[str]) -> np.ndarray:
        if not self.vocabulary_:
            return np.zeros((len(documents), 1 if self.max_features == 1 else 0), dtype=np.float64)
            
        N = len(documents)
        V = len(self.vocabulary_)
        X = np.zeros((N, V), dtype=np.float64)
        
        for i, doc in enumerate(documents):
            tokens = self._tokenize(doc)
            ngrams = self._get_ngrams(tokens)
            
            term_counts = Counter(ngrams)
            
            for term, count in term_counts.items():
                if term in self.vocabulary_:
                    idx = self.vocabulary_[term]
                    if self.sublinear_tf:
                        tf = 1.0 + math.log(count) if count > 0 else 0.0
                    else:
                        tf = count
                    X[i, idx] = tf * self.idf_[idx]
                    
        row_norms = np.linalg.norm(X, axis=1, keepdims=True)
        X = np.divide(X, row_norms, out=np.zeros_like(X), where=row_norms!=0)
        
        return X

    def fit_transform(self, documents: Sequence[str]) -> np.ndarray:
        return self.fit(documents).transform(documents)

    def get_feature_names(self) -> List[str]:
        return self.feature_names_

    def get_feature_names_out(self) -> List[str]:
        return self.feature_names_

TFIDFTraceVectorizer = TraceVectorizer
