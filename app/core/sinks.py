from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from loguru import logger

from app.core.models import MetricPoint, TriggerEvent
from app.notify.telegram.messages import build_trigger_message
from app.notify.telegram.sender import send_telegram_message


class Sink:
    async def on_metric(self, mp: MetricPoint) -> None:
        return

    async def on_trigger(self, ev: TriggerEvent) -> None:
        return


@dataclass
class LoggerSink(Sink):
    level: str = "INFO"
    log_metrics: bool = False

    async def on_metric(self, mp: MetricPoint) -> None:
        if not self.log_metrics:
            return

        logger.log(
            self.level,
            "METRIC | pair={} | {}={:.6f} | bid_vol={:.6f} ask_vol={:.6f}",
            mp.pair,
            mp.name,
            mp.value,
            mp.bid_volume,
            mp.ask_volume,
        )

    async def on_trigger(self, ev: TriggerEvent) -> None:
        logger.success("✅ SUCCESS | TRIGGER | pair={} | {}", ev.pair, ev.message)


@dataclass
class TelegramSink(Sink):
    bot_token: str
    chat_id: str
    enabled: bool = True

    async def on_trigger(self, ev: TriggerEvent) -> None:
        if not self.enabled:
            return

        text = build_trigger_message(ev)
        await send_telegram_message(self.bot_token, self.chat_id, text)


def _read_telegram_cfg(tg: Any) -> tuple[bool, str, str]:
    """
    Підтримує:
      - dict: {"enabled":..., "bot_token":..., "chat_id":...}
      - dataclass/obj: tg.enabled, tg.bot_token, tg.chat_id
    """
    if tg is None:
        return False, "", ""

    # dict
    if isinstance(tg, dict):
        enabled = bool(tg.get("enabled", False))
        token = str(tg.get("bot_token", "")).strip()
        chat_id = str(tg.get("chat_id", "")).strip()
        return enabled, token, chat_id

    # dataclass/object
    enabled = bool(getattr(tg, "enabled", False))
    token = str(getattr(tg, "bot_token", "")).strip()
    chat_id = str(getattr(tg, "chat_id", "")).strip()
    return enabled, token, chat_id


def build_sinks(cfg: dict) -> List[Sink]:
    sinks: List[Sink] = []

    for s in (cfg.get("sinks") or []):
        st = (s.get("type") or "").lower()

        if st == "logger":
            sinks.append(
                LoggerSink(
                    level=str(s.get("level", "INFO")),
                    log_metrics=bool(s.get("log_metrics", False)),
                )
            )

    tg_enabled, tg_token, tg_chat_id = _read_telegram_cfg(cfg.get("telegram"))

    if tg_enabled and tg_token and tg_chat_id:
        sinks.append(TelegramSink(bot_token=tg_token, chat_id=tg_chat_id, enabled=True))
    elif tg_enabled:
        logger.warning("Telegram enabled, but bot_token/chat_id missing -> TelegramSink disabled")

    if not sinks:
        sinks.append(LoggerSink(level="INFO", log_metrics=False))

    return sinks
