from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional

import websockets
from loguru import logger
from websockets.exceptions import ConnectionClosed, WebSocketException


def build_depth_streams(pairs: Iterable[str], depth_stream: str) -> List[str]:
    ds = (depth_stream or "").strip()
    if not ds:
        raise ValueError("depth_stream is empty (expected like 'depth10@100ms').")

    out: List[str] = []
    for p in pairs:
        p = (p or "").strip()
        if not p:
            continue
        out.append(f"{p.lower()}@{ds}")

    if not out:
        raise ValueError("No valid pairs provided.")
    return out


@dataclass(frozen=True)
class BinanceWSOptions:
    ws_url: str
    pairs: List[str]
    depth_stream: str

    ping_interval: int = 20
    ping_timeout: int = 20

    reconnect_min_delay: float = 0.5
    reconnect_max_delay: float = 15.0
    reconnect_backoff: float = 1.7
    reconnect_jitter: float = 0.25

    subscribe_batch_size: int = 50


class BinanceWSClient:
    def __init__(self, opts: BinanceWSOptions):
        self.opts = opts
        self._stop_event = asyncio.Event()
        self._ws: Optional[Any] = None
        self._sub_id = 1

    def stop(self) -> None:
        self._stop_event.set()

    async def __aenter__(self) -> "BinanceWSClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.stop()
        await self._close_ws()

    async def _close_ws(self) -> None:
        ws = self._ws
        self._ws = None
        if ws is None:
            return
        try:
            await ws.close()
        except Exception:
            pass

    async def _connect(self) -> Any:
        logger.info("Connecting to Binance WS: {}", self.opts.ws_url)
        ws = await websockets.connect(
            self.opts.ws_url,
            ping_interval=self.opts.ping_interval,
            ping_timeout=self.opts.ping_timeout,
            close_timeout=5,
            max_queue=1000,
        )
        self._ws = ws
        return ws

    async def _subscribe(self, ws: Any) -> None:
        streams = build_depth_streams(self.opts.pairs, self.opts.depth_stream)

        batch_size = max(1, int(self.opts.subscribe_batch_size))
        total_batches = (len(streams) + batch_size - 1) // batch_size

        for i in range(0, len(streams), batch_size):
            chunk = streams[i : i + batch_size]
            msg = {"method": "SUBSCRIBE", "params": chunk, "id": self._sub_id}
            self._sub_id += 1

            await ws.send(json.dumps(msg))
            logger.info(
                "Subscribed: batch {}/{} | streams={}",
                i // batch_size + 1,
                total_batches,
                len(chunk),
            )

    async def messages(self) -> AsyncIterator[Dict[str, Any]]:
        delay = self.opts.reconnect_min_delay

        while not self._stop_event.is_set():
            try:
                ws = await self._connect()
                await self._subscribe(ws)
                delay = self.opts.reconnect_min_delay

                async for raw in ws:
                    if self._stop_event.is_set():
                        break
                    if not raw:
                        continue

                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning("JSON decode error. Raw={}", str(raw)[:300])
                        continue

                    yield data

            except (ConnectionClosed, WebSocketException, OSError) as e:
                if self._stop_event.is_set():
                    break
                logger.warning("WS disconnected: {}", e)

            except Exception as e:
                if self._stop_event.is_set():
                    break
                logger.exception("Unexpected WS error: {}", e)

            finally:
                await self._close_ws()

            if self._stop_event.is_set():
                break

            jitter = 1.0 + (random.random() * 2 - 1) * self.opts.reconnect_jitter
            sleep_for = min(self.opts.reconnect_max_delay, max(0.0, delay * jitter))
            logger.info("Reconnecting in {:.2f}s ...", sleep_for)
            await asyncio.sleep(sleep_for)
            delay = min(self.opts.reconnect_max_delay, delay * self.opts.reconnect_backoff)
