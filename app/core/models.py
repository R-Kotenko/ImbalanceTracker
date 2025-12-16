from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class Level:
    price: float
    qty: float


@dataclass
class OrderBook:
    pair: str
    bids: List[Level]
    asks: List[Level]
    last_update_id: Optional[int] = None
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class MetricPoint:
    pair: str
    name: str
    value: float
    bid_volume: float
    ask_volume: float
    ts: datetime


@dataclass(frozen=True)
class TriggerEvent:
    pair: str
    trigger_name: str
    metric: str
    metric_value: float
    bid_volume: float
    ask_volume: float
    ts: datetime
    message: str
