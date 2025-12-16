from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from loguru import logger

from app.core.config import load_config
from app.core.metrics import calc_imbalance_ratio
from app.core.sinks import build_sinks
from app.core.triggers import TriggerConfig, TriggerEngine
from app.core.gateway import create_gateway

from app.exchanges.binance.ws import BinanceWSClient, BinanceWSOptions
from app.exchanges.binance.parser import parse_depth_event


# ---- middlewares ----
async def drop_subscribe_acks(msg: Dict[str, Any]):
    if "result" in msg and "id" in msg and msg.get("result") is None:
        return None
    return msg


async def only_depth_streams(msg: Dict[str, Any]):
    stream = msg.get("stream")
    if isinstance(stream, str):
        return msg if "@depth" in stream else None
    return msg


def build_trigger_engine(cfg_triggers: List[Dict[str, Any]]) -> TriggerEngine:
    triggers: List[TriggerConfig] = []
    for t in cfg_triggers:
        triggers.append(
            TriggerConfig(
                name=str(t.get("name")),
                metric=str(t.get("metric", "imbalance_ratio")),
                op=str(t.get("op", ">=")),
                value=float(t.get("value", 0.0)),
                cooldown_sec=float(t.get("cooldown_sec", 0.0)),
                emit=str(t.get("emit", "edge")),
            )
        )
    return TriggerEngine(triggers)


async def run_async(config_path: str) -> None:
    cfg = load_config(config_path)

    sinks = build_sinks({"sinks": cfg.sinks, "telegram": cfg.telegram})
    engine = build_trigger_engine(cfg.triggers)

    ws_opts = BinanceWSOptions(
        ws_url=cfg.binance.ws_url,
        pairs=cfg.pairs,
        depth_stream=cfg.binance.depth_stream,
    )
    ws = BinanceWSClient(ws_opts)

    async def handle_depth(ev: Dict[str, Any]) -> None:
        ob = parse_depth_event(ev, top_n=cfg.binance.top_n)
        if not ob:
            return

        mp = calc_imbalance_ratio(ob, volume_mode=cfg.metrics.volume_mode)

        for s in sinks:
            await s.on_metric(mp)

        events = engine.process(mp)
        for e in events:
            for s in sinks:
                await s.on_trigger(e)

    gateway = create_gateway(
        middlewares=[drop_subscribe_acks, only_depth_streams],
        on_depth=[handle_depth],
        queue_max=5000,
    )

    task_gateway = asyncio.create_task(gateway.run())

    logger.info("Runner started | pairs={} | stream={}", cfg.pairs, cfg.binance.depth_stream)

    try:
        async for raw in ws.messages():
            await gateway.push(raw)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt -> stopping...")
    finally:
        ws.stop()
        gateway.stop()
        await asyncio.sleep(0.2)
        task_gateway.cancel()


def run(config_path: str) -> None:
    asyncio.run(run_async(config_path))
