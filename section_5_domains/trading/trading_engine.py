from mind.organ import Organ

class TradingOrgan(Organ):
    name = "trading"
    kind = "domain"
    scope = "outside_guards"
    capabilities = ["analyze", "forecast", "backtest"]
    keywords = ["trade", "trading", "btc", "bitcoin", "crypto", "binance", "rsi", "ema", "market", "strategy"]

    def can_handle(self, request):
        text = (request.get("text") or "").lower()
        return any(k in text for k in self.keywords)

    def handle(self, request):
        return {"status": "ok", "output": f"[trading] Received: {request.get('text')}"}

ORGAN = TradingOrgan()