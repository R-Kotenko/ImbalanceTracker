from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yaml


@dataclass(frozen=True)
class BinanceCfg:
    ws_url: str
    depth_stream: str
    top_n: int = 10


@dataclass(frozen=True)
class MetricsCfg:
    volume_mode: str = "notional"   # qty | notional


@dataclass(frozen=True)
class TelegramCfg:
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


@dataclass(frozen=True)
class AppCfg:
    pairs: List[str]
    binance: BinanceCfg
    metrics: MetricsCfg
    triggers: List[Dict[str, Any]]
    sinks: List[Dict[str, Any]]
    telegram: TelegramCfg


def load_config(path: str) -> AppCfg:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    pairs = list(raw.get("pairs") or [])

    b = raw.get("binance") or {}
    m = raw.get("metrics") or {}
    tg = raw.get("telegram") or {}

    return AppCfg(
        pairs=pairs,
        binance=BinanceCfg(
            ws_url=str(b.get("ws_url", "wss://stream.binance.com:9443/stream")),
            depth_stream=str(b.get("depth_stream", "depth10@100ms")),
            top_n=int(b.get("top_n", 10)),
        ),
        metrics=MetricsCfg(
            volume_mode=str(m.get("volume_mode", "qty")),
        ),
        triggers=list(raw.get("triggers") or []),
        sinks=list(raw.get("sinks") or []),
        telegram=TelegramCfg(
            enabled=bool(tg.get("enabled", False)),
            bot_token=str(tg.get("bot_token", "")).strip(),
            chat_id=str(tg.get("chat_id", "")).strip(),
        ),
    )
