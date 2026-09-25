import re
from typing import Optional, List, Union, Any
from dataclasses import dataclass

@dataclass
class ErrorSpan:
    text: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    exception_type: Optional[str] = None
    message: Optional[str] = None

    def __str__(self):
        return self.text

    def __repr__(self):
        return self.text

    def __len__(self):
        return len(self.text)

    def __getitem__(self, item):
        return self.text[item]

    def split(self, *args, **kwargs):
        return self.text.split(*args, **kwargs)

    def strip(self, *args, **kwargs):
        return self.text.strip(*args, **kwargs)
        
    def lower(self):
        return self.text.lower()

    def __contains__(self, item):
        return item in self.text


class TraceMiner:
    def __init__(self):
        self.mem_regex = re.compile(r'0x[0-9a-fA-F]+')
        self.pid_regex = re.compile(r'\b(PID|pid|process|Process)\s*[:=]?\s*\d+\b')
        self.line_regex = re.compile(r'\bline\s+\d+\b')
        self.tmp_regex = re.compile(r'/tmp/[^:\s\'"]+')

    def normalize_error(self, raw: str) -> str:
        if not raw:
            return ""
        raw = self.mem_regex.sub('[MEM_ADDR]', raw)
        raw = self.pid_regex.sub('[PID]', raw)
        raw = self.line_regex.sub('line [LINE]', raw)
        raw = self.tmp_regex.sub('[TMP_PATH]', raw)
        return raw

    def extract_error_span(self, text: Optional[str]) -> str:
        if not text or not text.strip():
            return ""
        
        # Clean corrupted bytes
        text = text.replace('\x00', '').replace('\xff\xfe', '')

        # Handle large texts: if > 50000, keep last 45000 chars to get exception tail
        if len(text) > 50000:
            text = text[-45000:]
            
        tb_marker = "Traceback (most recent call last):"
        if tb_marker in text:
            blocks = text.split(tb_marker)
            tb_block = tb_marker + blocks[-1]
            return self.normalize_error(tb_block.strip())
            
        # If no Traceback, look for lines with Exception/Error
        lines = text.splitlines()
        err_lines = [line for line in lines if "Error" in line or "Exception" in line]
        if err_lines:
            return self.normalize_error("\n".join(err_lines).strip())
        
        return self.normalize_error(text.strip())

    def extract_error_spans(self, traces: Union[str, List[Any], None]) -> List[Any]:
        if traces is None:
            return []
        if isinstance(traces, str):
            if not traces.strip():
                return []
            traces = [traces]
            
        spans = []
        for t in traces:
            if t is None:
                continue
            raw_text = ""
            if hasattr(t, "raw_error_message"):
                raw_text = t.raw_error_message or ""
            elif isinstance(t, str):
                raw_text = t
            elif hasattr(t, "__str__"):
                raw_text = str(t)
                
            if not raw_text or not raw_text.strip():
                continue

            text = self.extract_error_span(raw_text)
            if text and text.strip():
                spans.append(ErrorSpan(text=text))
            
        return spans

    def cluster_failures(self, traces: List[str], k_clusters: int = 3):
        from .archetypes import ArchetypeClusterer
        return ArchetypeClusterer(k_clusters=k_clusters).fit_predict(traces)


def extract_error_spans(traces: Union[str, List[Any]]) -> List[Any]:
    return TraceMiner().extract_error_spans(traces)
