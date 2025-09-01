import asyncio
import time
from typing import Callable, Any, Optional
from app.observability.logger import get_logger

log = get_logger()

class RetryManager:
    """재시도 로직을 관리하는 유틸리티 클래스"""
    
    def __init__(
        self,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 120.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
    
    async def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str = "operation",
        *args,
        **kwargs
    ) -> Any:
        """재시도 로직으로 작업을 실행합니다."""
        last_exception = None
        delay = self.initial_delay
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                if attempt > 0:
                    log.info(f"{operation_name} 성공 (시도 {attempt + 1}/{self.max_retries + 1})")
                return result
                
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    # 지터 추가 (동시 재시도 방지)
                    actual_delay = delay
                    if self.jitter:
                        import random
                        actual_delay = delay * (0.5 + random.random() * 0.5)
                    
                    log.warning(
                        f"{operation_name} 실패 (시도 {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"{actual_delay:.1f}초 후 재시도..."
                    )
                    
                    await asyncio.sleep(actual_delay)
                    delay = min(delay * self.backoff_factor, self.max_delay)
                else:
                    log.error(f"{operation_name} 최종 실패: {e}")
                    raise last_exception
    
    def get_delay_for_attempt(self, attempt: int) -> float:
        """특정 시도에 대한 지연 시간을 계산합니다."""
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)

# 기본 재시도 매니저 인스턴스
default_retry_manager = RetryManager()
