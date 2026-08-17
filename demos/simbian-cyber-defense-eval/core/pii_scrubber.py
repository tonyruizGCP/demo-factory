"""PII and Sensitive Data Redaction Pipeline for Agent Logging and Memory."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Union


class PIIScrubber:
    """Detects and redacts personally identifiable information (PII) and credentials."""

    # Patterns for sensitive entities
    PATTERNS = {
        "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "API_KEY": re.compile(r"(?i)\b(AIza[0-9A-Za-z-_]{20,50}|sk-[a-zA-Z0-9]{20,60}|ghp_[a-zA-Z0-9]{20,50})\b"),
        "BEARER_TOKEN": re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{15,}"),
        "PASSWORD_FIELD": re.compile(r'(?i)(password|secret|passwd|token)["\']?\s*[:=]\s*["\']?([^"\'\s,;]+)'),
        "IPV4_PRIVATE": re.compile(r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"),
        "CREDENTIAL_DOMAIN_USER": re.compile(r"(?i)\b([a-zA-Z0-9_-]+\\[a-zA-Z0-9_.-]+:[^\s,;]+)\b"),
    }

    @classmethod
    def redact_text(cls, text: str, preserve_soc_hosts: bool = True) -> str:
        """Redact sensitive patterns in text string.

        Args:
            text: Raw input text string.
            preserve_soc_hosts: If True, preserves benign simulated host identifiers while masking private secrets.

        Returns:
            str: Sanitized text with redacted PII tokens.
        """
        if not text or not isinstance(text, str):
            return text

        scrubbed = text

        # Redact API Keys
        scrubbed = cls.PATTERNS["API_KEY"].sub("[REDACTED_API_KEY]", scrubbed)

        # Redact Bearer Tokens
        scrubbed = cls.PATTERNS["BEARER_TOKEN"].sub("Bearer [REDACTED_TOKEN]", scrubbed)

        # Redact Password assignments
        scrubbed = cls.PATTERNS["PASSWORD_FIELD"].sub(r'\1: "[REDACTED_SECRET]"', scrubbed)

        # Redact Emails
        scrubbed = cls.PATTERNS["EMAIL"].sub("[REDACTED_EMAIL]", scrubbed)

        # Redact domain user passwords (e.g. DOMAIN\user:password)
        scrubbed = cls.PATTERNS["CREDENTIAL_DOMAIN_USER"].sub("[REDACTED_CREDENTIALS]", scrubbed)

        return scrubbed

    @classmethod
    def sanitize_object(cls, obj: Any) -> Any:
        """Recursively traverse and sanitize dictionaries, lists, or strings.

        Args:
            obj: Dict, list, string, or primitive object.

        Returns:
            Any: Sanitized data structure with scrubbed PII.
        """
        if isinstance(obj, str):
            return cls.redact_text(obj)
        elif isinstance(obj, dict):
            return {k: cls.sanitize_object(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [cls.sanitize_object(item) for item in obj]
        return obj
