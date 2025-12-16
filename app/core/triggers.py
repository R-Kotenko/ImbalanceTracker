from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.core.models import MetricPoint, TriggerEvent


@dataclass(frozen=True)
class TriggerConfig:
    name: str
    metric: str               # "imbalance_ratio"
    op: str                   # ">=", "<=", ">", "<", "=="
    value: float
    cooldown_sec: float = 0.0
    emit: str = "edge"        # "edge" | "always"


@dataclass
class _TriggerState:
    last_emit_ts: Optional[datetime] = None
    last_condition: Optional[bool] = None


def compare(op: str, a: float, b: float) -> bool:
    if op == ">=":
        return a >= b
    if op == "<=":
        return a <= b
    if op == ">":
        return a > b
    if op == "<":
        return a < b
    if op == "==":
        return a == b
    raise ValueError(f"Unsupported op: {op}")


def can_emit_edge(prev: Optional[bool], current: bool) -> bool:
    # edge: emit тільки на переході False/None -> True
    if not current:
        return False
    return (prev is False) or (prev is None)


def cooldown_passed(last_ts: Optional[datetime], now: datetime, cooldown_sec: float) -> bool:
    if cooldown_sec <= 0:
        return True
    if last_ts is None:
        return True
    return (now - last_ts).total_seconds() >= cooldown_sec


class TriggerEngine:
    def __init__(self, triggers: List[TriggerConfig]):
        self.triggers = triggers
        self.state: Dict[str, _TriggerState] = {}  # key = "PAIR|trigger_name"

    def process(self, mp: MetricPoint) -> List[TriggerEvent]:
        events: List[TriggerEvent] = []

        now = mp.ts or datetime.now(timezone.utc)

        for t in self.triggers:
            if t.metric != mp.name:
                continue

            key = f"{mp.pair}|{t.name}"
            st = self.state.get(key)
            if st is None:
                st = _TriggerState()

            cond = compare(t.op, mp.value, t.value)

            if cond:
                if not cooldown_passed(st.last_emit_ts, now, t.cooldown_sec):
                    st.last_condition = cond
                    self.state[key] = st
                    continue

                if t.emit == "always":
                    should_emit = True
                else:
                    should_emit = can_emit_edge(st.last_condition, cond)

                if should_emit:
                    st.last_emit_ts = now

                    msg = (
                        f"{t.name}: {mp.name} {t.op} {t.value} | "
                        f"value={mp.value:.6f} | "
                        f"bid={mp.bid_volume:.6f} ask={mp.ask_volume:.6f}"
                    )

                    events.append(
                        TriggerEvent(
                            pair=mp.pair,
                            trigger_name=t.name,
                            metric=mp.name,
                            metric_value=mp.value,
                            bid_volume=mp.bid_volume,
                            ask_volume=mp.ask_volume,
                            ts=now,
                            message=msg,
                        )
                    )

            st.last_condition = cond
            self.state[key] = st

        return events
