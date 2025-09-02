from __future__ import annotations
import logging
from loguru import logger

# ---- stdlib logging → loguru 인터셉트 ----
class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except Exception:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())

def _hook_stdlib_logging() -> None:
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    # 시끄러운 로거는 필요 시 레벨만 조정 가능
    for noisy in ("uvicorn", "gunicorn", "asyncio", "sqlalchemy"):
        l = logging.getLogger(noisy)
        l.handlers = [InterceptHandler()]
        l.propagate = False

# ---- 개발 콘솔 포맷(사람 친화, extra 미노출) ----
DEV_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level:<7}</level> | "
    "<cyan>{name}</cyan> | "
    "<cyan>{file}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

def setup_logging_dev(log_level: str = "INFO") -> None:
    """
    개발 콘솔 전용 loguru 초기화.
    - 콘솔 컬러 출력
    - stdlib logging 흡수
    """
    logger.remove()  # 기본 sink 제거
    logger.add(
        sink=lambda m: print(m, end=""),
        format=DEV_FORMAT,
        colorize=True,
        backtrace=True,   # dev에서만 편의상 True
        diagnose=False,   # 과도한 진단은 끔
        level=log_level.upper(),
        enqueue=False,    # 콘솔은 큐 불필요
    )
    _hook_stdlib_logging()

def get_logger(name: str = "dxsafety", **ctx):
    """선택적으로 컨텍스트를 바인딩한 logger 반환."""
    return logger.bind(name=name, **ctx)

def with_context(**ctx):
    """컨텍스트 매니저로 일시 컨텍스트 부여."""
    return logger.contextualize(**ctx)

# 기존 코드와의 호환성을 위한 별칭
setup_logger = setup_logging_dev
