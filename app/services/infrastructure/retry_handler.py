"""
Retry Handler — Exponential backoff with jitter for transient failures.
"""

import asyncio
import random
import logging
from typing import Any, Callable, Optional, Tuple, Type

logger = logging.getLogger(__name__)

# HTTP status codes that are safe to retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404, 405, 422}


class RetryableError(Exception):
    """Raised to signal that an operation should be retried."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class NonRetryableError(Exception):
    """Raised to signal that an operation should NOT be retried."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


async def retry_with_backoff(
    fn: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        ConnectionError, TimeoutError, OSError, RetryableError
    ),
    operation_name: str = "operation",
) -> Any:
    """
    Execute a function with exponential backoff retry.

    Args:
        fn: Async callable to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        jitter: Add random jitter to prevent thundering herd
        retryable_exceptions: Tuple of exception types to retry on
        operation_name: Name for logging

    Returns:
        Result of fn()

    Raises:
        Last exception if all retries exhausted
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(fn):
                return await fn()
            else:
                return fn()

        except NonRetryableError:
            raise  # Never retry these

        except retryable_exceptions as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(
                    f"Retry [{operation_name}] exhausted after {max_retries} attempts. "
                    f"Last error: {e}"
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** attempt), max_delay)
            if jitter:
                delay += random.uniform(0, delay * 0.3)

            logger.warning(
                f"Retry [{operation_name}] attempt {attempt + 1}/{max_retries} "
                f"after {delay:.1f}s. Error: {type(e).__name__}: {e}"
            )
            await asyncio.sleep(delay)

        except Exception as e:
            # Unknown exception — don't retry
            logger.error(f"Retry [{operation_name}] non-retryable error: {e}")
            raise

    raise last_exception  # Should never reach here


def retry_sync(
    fn: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        ConnectionError, TimeoutError, OSError
    ),
    operation_name: str = "operation",
) -> Any:
    """Synchronous version of retry_with_backoff."""
    import time

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return fn()
        except retryable_exceptions as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(
                    f"Retry [{operation_name}] exhausted after {max_retries} attempts."
                )
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay += random.uniform(0, delay * 0.3)
            logger.warning(
                f"Retry [{operation_name}] attempt {attempt + 1}/{max_retries} "
                f"after {delay:.1f}s"
            )
            time.sleep(delay)
        except Exception:
            raise

    raise last_exception


def is_retryable_status(status_code: int) -> bool:
    """Check if an HTTP status code is retryable."""
    return status_code in RETRYABLE_STATUS_CODES
