"""
Retry utilities for DX-Safety.

This module provides retry and backoff utilities
for reliable operation in distributed systems.
"""

import asyncio
import random
from typing import Callable, Awaitable, TypeVar

T = TypeVar('T')

async def exponential_backoff(attempt: int, base: float, max_delay: float) -> None:
    """
    지수 백오프 지연을 수행합니다.
    
    Args:
        attempt: 현재 시도 횟수 (1부터 시작)
        base: 기본 지연 시간 (초)
        max_delay: 최대 지연 시간 (초)
    """
    delay = min(max_delay, base * (2 ** max(0, attempt - 1)))
    await asyncio.sleep(delay)

async def retry_with_backoff(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> T:
    """
    지수 백오프와 함께 함수를 재시도합니다.
    
    Args:
        func: 재시도할 비동기 함수
        max_retries: 최대 재시도 횟수
        base_delay: 기본 지연 시간 (초)
        max_delay: 최대 지연 시간 (초)
        jitter: 지터 적용 여부
        
    Returns:
        함수 실행 결과
        
    Raises:
        마지막 시도에서 발생한 예외
    """
    last_exception = None
    
    for attempt in range(1, max_retries + 2):  # +2 because we try once + max_retries
        try:
            return await func()
        except Exception as e:
            last_exception = e
            
            if attempt > max_retries:
                break
            
            # 지연 계산
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            
            # 지터 적용
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)
            
            await asyncio.sleep(delay)
    
    raise last_exception
