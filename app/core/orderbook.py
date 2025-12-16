from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, List, Optional

from app.core.models import Level, OrderBook


def to_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None


def parse_levels(raw: Iterable[Iterable[Any]], top_n: int, *, reverse: bool) -> List[Level]:
    levels: List[Level] = []

    for row in raw:
        if not row or len(row) < 2:
            continue

        price = to_float(row[0])
        qty = to_float(row[1])
        if price is None or qty is None:
            continue
        if qty <= 0:
            continue

        levels.append(Level(price=price, qty=qty))

        if len(levels) >= top_n:
            break

    # інколи може прийти неідеально відсортовано
    levels.sort(key=lambda x: x.price, reverse=reverse)

    return levels[:top_n]


def build_orderbook(
    *,
    pair: str,
    bids_raw: Iterable[Iterable[Any]],
    asks_raw: Iterable[Iterable[Any]],
    top_n: int,
    last_update_id: Optional[int] = None,
) -> OrderBook:
    bids = parse_levels(bids_raw, top_n=top_n, reverse=True)
    asks = parse_levels(asks_raw, top_n=top_n, reverse=False)

    return OrderBook(
        pair=pair.upper(),
        bids=bids,
        asks=asks,
        last_update_id=last_update_id,
        updated_at=datetime.now(timezone.utc),
    )
