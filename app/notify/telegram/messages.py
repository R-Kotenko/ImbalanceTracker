from __future__ import annotations

from datetime import timezone

from app.core.models import TriggerEvent


def build_trigger_message(ev: TriggerEvent) -> str:
    ts = ev.ts
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    bid = float(ev.bid_volume)
    ask = float(ev.ask_volume)
    net = bid - ask
    ratio = float(ev.metric_value)
    bid_ask = (bid / ask) if ask > 0 else 0.0

    direction = "🟢 Direction: BUY" if ratio >= 0 else "🔴 Direction: SELL"

    return (
        "✅ NEW IMBALANCE ALERT 🚨\n"
        "\n"
        f"📌 Pair: {ev.pair}\n"
        f"🎯 Trigger: {ev.trigger_name}\n"
        f"{direction}\n"
        "\n"
        f"⚡️ Metric: {ev.metric} = {ratio:.6f}\n"
        f"⚖️ Imbalance: {ratio * 100:+.2f}% of (Bid+Ask)\n"
        "\n"
        "📚 Top-10 order book volumes:\n"
        f"ℹ️ Bid: {bid:,.2f}/Ask: {ask:,.2f}\n"
        f"📊 Net (Bid-Ask): {net:+,.2f}\n"
        f"📈 Bid/Ask: {bid_ask:.3f}x\n"
        "\n"
        f"🕒 Time (UTC): {ts.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
