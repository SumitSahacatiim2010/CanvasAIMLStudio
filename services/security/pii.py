"""PII Detection Module — scanning and masking of sensitive data.

Blueprint §8: Scans incoming data and documents for PII/NPI.
Provides masking capabilities before data enters the ML or Agentic pipeline.
"""

from typing import Any
import re


class PIIScanner:
    """Detects and masks Personally Identifiable Information."""

    def __init__(self) -> None:
        # Regex patterns for common Indian and Global PII
        self.patterns = {
            "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b',
            "PHONE_IN": r'\b(?:\+?91|0)?[6789]\d{9}\b',
            "PAN_CARD": r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b',
            "AADHAAR": r'\b\d{4}\s?\d{4}\s?\d{4}\b',
            "CREDIT_CARD": r'\b(?:\d[ -]*?){13,16}\b',
            "SSN_US": r'\b\d{3}-\d{2}-\d{4}\b',
        }
        self.compiled_patterns = {k: re.compile(v) for k, v in self.patterns.items()}

    def detect(self, text: str) -> dict[str, list[str]]:
        """Detect PII in text and return matches by category."""
        if not text:
            return {}

        results: dict[str, list[str]] = {}
        for category, pattern in self.compiled_patterns.items():
            matches = pattern.findall(text)
            if matches:
                results[category] = list(set(matches))

        return results

    def mask(self, text: str, mask_char: str = "*", preserve_last: int = 4) -> str:
        """Mask detected PII in text."""
        if not text:
            return text

        masked_text = text
        for category, pattern in self.compiled_patterns.items():
            def replacer(match: re.Match) -> str:
                matched_str = match.group(0)
                if category == "EMAIL":
                    parts = matched_str.split("@")
                    if len(parts) == 2:
                        return f"{parts[0][0]}{mask_char * max(1, len(parts[0])-1)}@{parts[1]}"
                elif len(matched_str) > preserve_last:
                    # Keep last N characters visible
                    return mask_char * (len(matched_str) - preserve_last) + matched_str[-preserve_last:]
                return mask_char * len(matched_str)

            masked_text = pattern.sub(replacer, masked_text)

        return masked_text

    def scan_dict(self, data: dict[str, Any]) -> dict[str, list[str]]:
        """Scan string values in a dictionary for PII."""
        findings: dict[str, list[str]] = {}
        for key, value in data.items():
            if isinstance(value, str):
                detected = self.detect(value)
                if detected:
                    findings[key] = list(detected.keys())
        return findings

    def mask_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Mask PII in string values of a dictionary."""
        result = data.copy()
        for key, value in result.items():
            if isinstance(value, str):
                result[key] = self.mask(value)
            elif isinstance(value, dict):
                result[key] = self.mask_dict(value)
        return result
