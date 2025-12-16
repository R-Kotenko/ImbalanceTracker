from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.models import OrderBook
from app.core.orderbook import build_orderbook


def parse_depth_event(ev: Dict[str, Any], *, top_n: int) -> Optional[OrderBook]:

    pair = (ev.get("_pair") or "").upper()
    if not pair:
        return None

    if "bids" in ev and "asks" in ev:
        bids = ev.get("bids") or []
        asks = ev.get("asks") or []
        last_id = ev.get("lastUpdateId")

        return build_orderbook(
            pair=pair,
            bids_raw=bids,
            asks_raw=asks,
            top_n=top_n,
            last_update_id=last_id if isinstance(last_id, int) else None,
        )

    if ev.get("e") == "depthUpdate":
        bids = ev.get("b") or []
        asks = ev.get("a") or []
        last_id = ev.get("u")

        return build_orderbook(
            pair=pair,
            bids_raw=bids,
            asks_raw=asks,
            top_n=top_n,
            last_update_id=last_id if isinstance(last_id, int) else None,
        )

    return None
