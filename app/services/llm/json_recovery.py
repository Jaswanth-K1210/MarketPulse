"""
JSON Recovery Pipeline — Multi-strategy JSON extraction from LLM output.
Ported from WorldMonitor's robust parsing patterns.
"""

import re
import json
import logging
from typing import Any, Optional, Set

logger = logging.getLogger(__name__)


def recover_json(
    raw_text: str,
    valid_enums: Optional[dict[str, Set[str]]] = None
) -> Optional[dict]:
    """
    Multi-strategy JSON recovery from LLM output.

    Strategies (tried in order):
    1. Direct JSON parse
    2. Strip markdown code blocks then parse
    3. Find first { and last }, extract substring, parse
    4. Regex extract individual fields
    5. Return None (triggers fallback)

    Args:
        raw_text: Raw LLM response (possibly with markdown, preamble, etc.)
        valid_enums: Optional dict of field_name -> set of valid values for validation.
                     e.g. {"level": {"critical", "high", "medium", "low"}}

    Returns:
        Parsed dict or None if all strategies fail
    """
    if not raw_text or not raw_text.strip():
        return None

    text = raw_text.strip()

    # Strategy 1: Direct parse
    parsed = _try_direct_parse(text)
    if parsed is not None:
        return _validate_enums(parsed, valid_enums)

    # Strategy 2: Strip markdown code blocks
    parsed = _try_strip_markdown(text)
    if parsed is not None:
        return _validate_enums(parsed, valid_enums)

    # Strategy 3: Extract JSON substring (first { to last })
    parsed = _try_extract_json_substring(text)
    if parsed is not None:
        return _validate_enums(parsed, valid_enums)

    # Strategy 4: Regex field extraction
    parsed = _try_regex_extraction(text)
    if parsed is not None:
        return _validate_enums(parsed, valid_enums)

    logger.warning(f"All JSON recovery strategies failed. Raw text: {text[:200]}...")
    return None


def _try_direct_parse(text: str) -> Optional[dict]:
    """Strategy 1: Direct JSON.parse()"""
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
            return result[0]
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _try_strip_markdown(text: str) -> Optional[dict]:
    """Strategy 2: Strip markdown code fences then parse."""
    # Match ```json ... ``` or ``` ... ```
    pattern = re.compile(r'```(?:json)?\s*\n?([\s\S]*?)```', re.IGNORECASE)
    match = pattern.search(text)
    if match:
        json_str = match.group(1).strip()
        try:
            result = json.loads(json_str)
            if isinstance(result, dict):
                return result
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
                return result[0]
        except (json.JSONDecodeError, ValueError):
            pass

    # Also try single backtick blocks
    pattern2 = re.compile(r'`([\s\S]*?)`')
    for match in pattern2.finditer(text):
        try:
            result = json.loads(match.group(1))
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            continue

    return None


def _try_extract_json_substring(text: str) -> Optional[dict]:
    """Strategy 3: Find first { and last }, extract and parse."""
    first_brace = text.find('{')
    last_brace = text.rfind('}')

    if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
        return None

    json_candidate = text[first_brace:last_brace + 1]
    try:
        result = json.loads(json_candidate)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # Try fixing common issues: trailing commas, single quotes
    fixed = _fix_common_json_issues(json_candidate)
    try:
        result = json.loads(fixed)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    return None


def _try_regex_extraction(text: str) -> Optional[dict]:
    """Strategy 4: Regex extract individual JSON fields."""
    result = {}

    # Extract string fields
    string_pattern = re.compile(r'"(\w+)"\s*:\s*"([^"]*)"')
    for match in string_pattern.finditer(text):
        result[match.group(1)] = match.group(2)

    # Extract numeric fields
    number_pattern = re.compile(r'"(\w+)"\s*:\s*(-?\d+\.?\d*)')
    for match in number_pattern.finditer(text):
        key = match.group(1)
        if key not in result:  # Don't override string matches
            try:
                val = float(match.group(2))
                result[key] = int(val) if val == int(val) else val
            except ValueError:
                pass

    # Extract boolean fields
    bool_pattern = re.compile(r'"(\w+)"\s*:\s*(true|false)', re.IGNORECASE)
    for match in bool_pattern.finditer(text):
        key = match.group(1)
        if key not in result:
            result[key] = match.group(2).lower() == 'true'

    if result:
        return result
    return None


def _fix_common_json_issues(text: str) -> str:
    """Fix common JSON formatting issues from LLMs."""
    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    # Replace single quotes with double quotes (crude but often works)
    # Only if no double quotes already present in values
    if "'" in text and '"' not in text[1:-1]:
        text = text.replace("'", '"')
    return text


def _validate_enums(parsed: dict, valid_enums: Optional[dict[str, Set[str]]]) -> Optional[dict]:
    """
    Validate parsed dict against enum whitelists.
    Returns None if any required enum field has invalid value.
    """
    if not valid_enums:
        return parsed

    for field, valid_values in valid_enums.items():
        if field in parsed:
            value = parsed[field]
            if isinstance(value, str) and value.lower() not in {v.lower() for v in valid_values}:
                logger.warning(
                    f"LLM returned invalid enum value for '{field}': '{value}'. "
                    f"Valid: {valid_values}"
                )
                return None

    return parsed
