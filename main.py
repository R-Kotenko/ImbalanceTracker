from app.logging_setup import setup_logging
from app.core.runner import run

if __name__ == "__main__":
    setup_logging("BinanceTestTracker")
    run("config/config.yaml")
