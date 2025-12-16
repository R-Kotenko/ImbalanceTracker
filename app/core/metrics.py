from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Literal

from app.core.models import Level, MetricPoint, OrderBook


VolumeMode = Literal["qty", "notional"]  # qty | price*qty


def calc_volume(levels: Iterable[Level], mode: VolumeMode) -> float:
    if mode == "notional":
        return sum(l.price * l.qty for l in levels)
    return sum(l.qty for l in levels)


def calc_imbalance_ratio(
    ob: OrderBook,
    *,
    volume_mode: VolumeMode = "qty",
    metric_name: str = "imbalance_ratio",
) -> MetricPoint:
    bid_vol = calc_volume(ob.bids, volume_mode)
    ask_vol = calc_volume(ob.asks, volume_mode)

    total = bid_vol + ask_vol
    if total > 0:
        ratio = (bid_vol - ask_vol) / total
    else:
        ratio = 0.0

    return MetricPoint(
        pair=ob.pair,
        name=metric_name,
        value=float(ratio),
        bid_volume=float(bid_vol),
        ask_volume=float(ask_vol),
        ts=datetime.now(timezone.utc),
    )
