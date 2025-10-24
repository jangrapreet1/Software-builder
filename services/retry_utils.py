"""
Async retry utilities with exponential backoff and jitter for resilient external API calls.
"""
from __future__ import annotations
import asyncio
import random
from typing import Any, Sequence


async def async_retry(coro_factory, retries: int = 3, base_delay: float = 1.0, max_delay: float = 8.0, retry_on: tuple[type[BaseException], ...] = (Exception,)) -> Any:
    """Retry an async operation with exponential backoff and jitter.
    coro_factory: zero-arg callable returning coroutine (so body can be recreated each attempt)
    """
    attempt = 0
    last_err: BaseException | None = None
    while attempt <= retries:
        try:
            return await coro_factory()
        except retry_on as e:
            last_err = e
            if attempt == retries:
                break
            # Exponential backoff with jitter
            sleep = min(max_delay, base_delay * (2 ** attempt))
            sleep = sleep * (0.5 + random.random())
            await asyncio.sleep(sleep)
            attempt += 1
    assert last_err is not None
    raise last_err


async def call_llm_with_retry(llm, messages: Sequence[Any], retries: int = 3) -> Any:
    async def _call():
        return await llm.ainvoke(messages)
    return await async_retry(_call, retries=retries)
