"""
LLM Output Sanitizer — Ported from WorldMonitor's battle-tested patterns.
Strips thinking tags, detects reasoning preambles, validates output quality.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================
# Thinking Tag Patterns (Complete blocks)
# ============================================================
THINKING_COMPLETE_PATTERNS = [
    re.compile(r'<think>[\s\S]*?</think>', re.IGNORECASE),
    re.compile(r'<\|thinking\|>[\s\S]*?<\|/thinking\|>', re.IGNORECASE),
    re.compile(r'<reasoning>[\s\S]*?</reasoning>', re.IGNORECASE),
    re.compile(r'<reflection>[\s\S]*?</reflection>', re.IGNORECASE),
    re.compile(r'<internal>[\s\S]*?</internal>', re.IGNORECASE),
    re.compile(r'<scratchpad>[\s\S]*?</scratchpad>', re.IGNORECASE),
]

# Unterminated thinking blocks (model started thinking, never closed)
THINKING_UNTERMINATED_PATTERNS = [
    re.compile(r'<think>[\s\S]*$', re.IGNORECASE),
    re.compile(r'<\|thinking\|>[\s\S]*$', re.IGNORECASE),
    re.compile(r'<reasoning>[\s\S]*$', re.IGNORECASE),
    re.compile(r'<reflection>[\s\S]*$', re.IGNORECASE),
    re.compile(r'<internal>[\s\S]*$', re.IGNORECASE),
    re.compile(r'<scratchpad>[\s\S]*$', re.IGNORECASE),
]

# ============================================================
# Reasoning Preamble Detection
# ============================================================
TASK_NARRATION_PATTERN = re.compile(
    r'^(we need to|i need to|let me|i\'ll |i should|first,? i|'
    r'okay,? so|alright|sure|here is|here\'s|step \d|'
    r'to analyze|to summarize|to classify|to evaluate|'
    r'let\'s |i will |i can |i would |looking at)',
    re.IGNORECASE
)

PROMPT_ECHO_PATTERN = re.compile(
    r'^(summarize the|classify the|analyze the|extract the|'
    r'rules:|here are the rules|you are a|your task is|'
    r'given the following|based on the|instructions:)',
    re.IGNORECASE
)

# ============================================================
# Minimum Output Length by Task Type
# ============================================================
MIN_OUTPUT_LENGTHS = {
    "classify": 10,
    "summarize": 20,
    "extract_relationships": 15,
    "cascade_inference": 15,
    "explain": 20,
    "risk_analysis": 15,
    "default": 10,
}


def strip_thinking_tags(text: str) -> str:
    """Remove all thinking/reasoning tags from LLM output."""
    result = text

    # Strip complete blocks first
    for pattern in THINKING_COMPLETE_PATTERNS:
        result = pattern.sub('', result)

    # Strip unterminated blocks (these eat everything after the opening tag)
    for pattern in THINKING_UNTERMINATED_PATTERNS:
        result = pattern.sub('', result)

    return result.strip()


def has_reasoning_preamble(text: str) -> bool:
    """
    Detect if the output starts with reasoning/task narration.
    This indicates the model is 'thinking aloud' instead of providing the answer.
    """
    # Check first line only
    first_line = text.strip().split('\n')[0].strip()

    if TASK_NARRATION_PATTERN.match(first_line):
        return True
    if PROMPT_ECHO_PATTERN.match(first_line):
        return True

    return False


def validate_output_length(text: str, task_type: str = "default") -> bool:
    """Check if output meets minimum length requirements."""
    min_length = MIN_OUTPUT_LENGTHS.get(task_type, MIN_OUTPUT_LENGTHS["default"])
    return len(text.strip()) >= min_length


def sanitize_llm_output(
    raw_text: str,
    task_type: str = "default",
    reject_on_preamble: bool = True
) -> Optional[str]:
    """
    Full sanitization pipeline for LLM output.

    Returns sanitized text, or None if output should be rejected.

    Pipeline:
    1. Strip thinking tags (complete + unterminated)
    2. Detect reasoning preambles
    3. Validate minimum length
    4. Strip leading/trailing whitespace

    Args:
        raw_text: Raw LLM response text
        task_type: Type of task (classify, summarize, etc.) for length validation
        reject_on_preamble: Whether to reject output with reasoning preambles

    Returns:
        Sanitized text or None if output is invalid/should be rejected
    """
    if not raw_text:
        logger.warning("LLM output is empty")
        return None

    # Step 1: Strip thinking tags
    cleaned = strip_thinking_tags(raw_text)

    if not cleaned:
        logger.warning("LLM output empty after stripping thinking tags")
        return None

    # Step 2: Check for reasoning preamble
    if reject_on_preamble and has_reasoning_preamble(cleaned):
        logger.warning(
            f"Reasoning preamble detected in LLM output (task={task_type}): "
            f"{cleaned[:80]}..."
        )
        return None

    # Step 3: Validate length
    if not validate_output_length(cleaned, task_type):
        logger.warning(
            f"LLM output too short after sanitization (task={task_type}): "
            f"'{cleaned[:50]}'"
        )
        return None

    return cleaned
