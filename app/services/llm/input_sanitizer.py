"""
Input Sanitizer — Truncation, HTML stripping, encoding validation before LLM calls.
Prevents token waste, context overflow, and injection.
"""

import re
import html
from typing import Optional

# Maximum lengths per input type
MAX_CONTENT_LENGTH = 3000
MAX_TITLE_LENGTH = 500
MAX_QUERY_LENGTH = 500
MAX_PROMPT_CONTEXT_LENGTH = 2000

# HTML tag pattern
HTML_TAG_PATTERN = re.compile(r'<[^>]+>')

# Control character pattern (keep newline and tab)
CONTROL_CHAR_PATTERN = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

# Excessive whitespace pattern
EXCESSIVE_WHITESPACE = re.compile(r'[ \t]{4,}')
EXCESSIVE_NEWLINES = re.compile(r'\n{3,}')

# Common boilerplate patterns from scraped content
BOILERPLATE_PATTERNS = [
    re.compile(r'cookie\s*(policy|notice|consent).*?(?:\n|$)', re.IGNORECASE),
    re.compile(r'subscribe\s*(to|for)\s*(our|the)\s*(newsletter|updates).*?(?:\n|$)', re.IGNORECASE),
    re.compile(r'(sign up|log in|create account).*?(?:\n|$)', re.IGNORECASE),
    re.compile(r'advertisement.*?(?:\n|$)', re.IGNORECASE),
    re.compile(r'share\s*(this|on)\s*(facebook|twitter|linkedin|x).*?(?:\n|$)', re.IGNORECASE),
]


def sanitize_content(text: Optional[str], max_length: int = MAX_CONTENT_LENGTH) -> str:
    """
    Sanitize article content for LLM input.

    Pipeline:
    1. HTML entity decode
    2. Strip HTML tags
    3. Remove control characters
    4. Remove common boilerplate
    5. Collapse excessive whitespace
    6. Truncate to max_length
    7. Ensure valid UTF-8
    """
    if not text:
        return ""

    result = text

    # 1. Decode HTML entities
    result = html.unescape(result)

    # 2. Strip HTML tags
    result = HTML_TAG_PATTERN.sub(' ', result)

    # 3. Remove control characters
    result = CONTROL_CHAR_PATTERN.sub('', result)

    # 4. Remove boilerplate
    for pattern in BOILERPLATE_PATTERNS:
        result = pattern.sub('', result)

    # 5. Collapse whitespace
    result = EXCESSIVE_WHITESPACE.sub(' ', result)
    result = EXCESSIVE_NEWLINES.sub('\n\n', result)
    result = result.strip()

    # 6. Truncate
    if len(result) > max_length:
        # Try to truncate at a sentence boundary
        truncated = result[:max_length]
        last_period = truncated.rfind('.')
        last_newline = truncated.rfind('\n')
        cut_point = max(last_period, last_newline)
        if cut_point > max_length * 0.7:  # Only use boundary if we keep 70%+
            result = truncated[:cut_point + 1]
        else:
            result = truncated

    # 7. Ensure valid UTF-8
    result = result.encode('utf-8', errors='ignore').decode('utf-8')

    return result


def sanitize_title(text: Optional[str]) -> str:
    """Sanitize a headline/title for LLM input."""
    if not text:
        return ""

    result = html.unescape(text)
    result = HTML_TAG_PATTERN.sub('', result)
    result = CONTROL_CHAR_PATTERN.sub('', result)
    result = ' '.join(result.split())  # Normalize whitespace
    result = result[:MAX_TITLE_LENGTH]
    return result.strip()


def sanitize_query(text: Optional[str]) -> str:
    """Sanitize a user query for LLM input."""
    if not text:
        return ""

    result = CONTROL_CHAR_PATTERN.sub('', text)
    result = ' '.join(result.split())
    result = result[:MAX_QUERY_LENGTH]
    return result.strip()


def sanitize_context(text: Optional[str]) -> str:
    """Sanitize context text injected into prompts (e.g., signal aggregator output)."""
    if not text:
        return ""

    result = CONTROL_CHAR_PATTERN.sub('', text)
    result = EXCESSIVE_NEWLINES.sub('\n\n', result)
    result = result[:MAX_PROMPT_CONTEXT_LENGTH]
    return result.strip()
