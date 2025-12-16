from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Dict, List, Optional

from loguru import logger

RawMsg = Dict[str, Any]
Middleware = Callable[[RawMsg], Awaitable[Optional[RawMsg]]]
Handler = Callable[[RawMsg], Awaitable[None]]


def pair_from_stream(stream: str) -> Optional[str]:
    # "btcusdt@depth10@100ms" -> "BTCUSDT"
    if not stream or "@" not in stream:
        return None
    sym = stream.split("@", 1)[0].strip()
    return sym.upper() if sym else None


def create_gateway(
    *,
    middlewares: List[Middleware],
    on_depth: List[Handler],
    queue_max: int = 5000,
):
    """
    Gateway = черга + фільтри + enrichment + routing.
    Повертає об'єкт з методами:
      - push(msg)
      - run()
      - stop()
    """
    q: asyncio.Queue[RawMsg] = asyncio.Queue(maxsize=queue_max)
    stop_event = asyncio.Event()

    async def apply_middlewares(msg: RawMsg) -> Optional[RawMsg]:
        cur: Optional[RawMsg] = msg
        for mw in middlewares:
            if cur is None:
                return None
            cur = await mw(cur)
        return cur

    def stop() -> None:
        stop_event.set()

    async def push(msg: RawMsg) -> None:
        if stop_event.is_set():
            return
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            logger.warning("Gateway queue is full -> drop message")

    async def run() -> None:
        logger.info("Gateway started")

        while not stop_event.is_set():
            msg = await q.get()
            try:
                out = await apply_middlewares(msg)
                if out is None:
                    continue

                stream = out.get("stream")
                data = out.get("data") if isinstance(out.get("data"), dict) else out

                if isinstance(stream, str):
                    p = pair_from_stream(stream)
                    if p:
                        data["_pair"] = p
                    data["_stream"] = stream

                if isinstance(data.get("s"), str) and data["s"]:
                    data["_pair"] = data["s"].upper()

                is_partial = ("bids" in data and "asks" in data)
                is_diff = (data.get("e") == "depthUpdate")

                if is_partial or is_diff:
                    for h in on_depth:
                        await h(data)

            except Exception as e:
                logger.exception("Gateway error: {}", e)
            finally:
                q.task_done()

        logger.info("Gateway stopped")

    return SimpleNamespace(push=push, run=run, stop=stop)
