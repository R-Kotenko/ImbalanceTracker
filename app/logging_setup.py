import os
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger


def setup_logging(app_name: str = "BinanceTestTrecker") -> None:
    logger.remove()

    BASE_DIR = Path(__file__).resolve().parents[1]
    LOG_DIR = BASE_DIR / "logs"
    os.makedirs(LOG_DIR, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    run_log_file = LOG_DIR / f"{app_name}.{ts}.log"

    current_log_file = LOG_DIR / f"{app_name}.log"

    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        level="DEBUG",
        format=fmt,
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )

    logger.add(
        str(run_log_file),
        level="DEBUG",
        enqueue=True,
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
        catch=True,
        delay=True,
    )

    logger.add(
        str(current_log_file),
        level="INFO",
        enqueue=True,
        encoding="utf-8",
        backtrace=False,
        diagnose=False,
        catch=True,
        delay=True,
    )

    logger.info("Logging initialized | app_name={} | logs_dir={}", app_name, str(LOG_DIR))
