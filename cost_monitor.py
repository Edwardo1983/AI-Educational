# Monitorizare costuri pentru free tier
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Mapping, Optional

DEFAULT_RETENTION_DAYS = 30
DATE_FORMAT = "%Y-%m-%d"
COST_PRECISION = Decimal("0.0001")


def _resolve_default_config():
    try:
        from config import ConfigFree  # type: ignore
        return ConfigFree
    except Exception as exc:  # pragma: no cover - fallback pentru optional import
        logging.debug("Nu s-a putut importa ConfigFree: %s", exc)
        return None


def _ensure_decimal(value: Any, precision: Decimal = COST_PRECISION) -> Decimal:
    if isinstance(value, Decimal):
        return value.quantize(precision, rounding=ROUND_HALF_UP)
    if isinstance(value, (int, float)):
        return Decimal(str(value)).quantize(precision, rounding=ROUND_HALF_UP)
    if isinstance(value, str):
        return Decimal(value).quantize(precision, rounding=ROUND_HALF_UP)
    raise TypeError(f"Valoare necunoscuta pentru conversie in Decimal: {value!r}")


class CostMonitor:
    """Monitorizeaza costurile pentru free tier tinand cont de model si tarife."""

    RATE_KEYS = {
        "input": "input_per_1k",
        "cached_input": "cached_input_per_1k",
        "output": "output_per_1k",
    }

    def __init__(
        self,
        cost_file: str = "daily_costs.json",
        daily_limit_usd: Any = Decimal("5.00"),
        pricing: Optional[Mapping[str, Mapping[str, Any]]] = None,
        default_model: Optional[str] = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        config_cls: Optional[Any] = None,
    ) -> None:
        self.cost_file = cost_file
        self.retention_days = retention_days
        self.daily_limit_usd = _ensure_decimal(daily_limit_usd)

        config_cls = config_cls or _resolve_default_config()
        if pricing is None:
            if config_cls is None:
                raise ValueError("Nu exista sursa de preturi pentru CostMonitor")
            pricing = getattr(config_cls, "MODELS")
            default_model = default_model or getattr(config_cls, "DEFAULT_MODEL")

        if default_model is None:
            raise ValueError("default_model trebuie specificat cand pricing este custom")

        self.pricing: Dict[str, Dict[str, Decimal]] = {
            model: {key: _ensure_decimal(value) for key, value in model_data.items()}
            for model, model_data in pricing.items()
        }
        self.default_model = default_model

    def log_usage(self, tokens_used: Any, model: Optional[str] = None) -> bool:
        """Salveaza utilizarea si aplica limitele zilnice."""
        model_name = model or self.default_model
        cost = self.calculate_cost(tokens_used, model_name)

        data = self.load_daily_data()
        self._cleanup_history(data)

        today_key = datetime.now().strftime(DATE_FORMAT)
        if today_key not in data:
            data[today_key] = {"tokens": 0, "cost": Decimal("0"), "requests": 0}

        total_tokens = self._total_tokens(tokens_used)
        entry = data[today_key]
        entry["tokens"] = entry.get("tokens", 0) + total_tokens
        entry["cost"] = _ensure_decimal(entry.get("cost", Decimal("0"))) + cost
        entry["requests"] = entry.get("requests", 0) + 1

        self.save_daily_data(data)

        if entry["cost"] > self.daily_limit_usd:
            logging.warning(
                "Limita zilnica de cost depasita: $%s",
                entry["cost"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            )
            return False
        return True

    def calculate_cost(self, tokens: Any, model: Optional[str] = None) -> Decimal:
        """Calculeaza costul folosind tarifele injectate."""
        model_name = model or self.default_model
        pricing = self.pricing.get(model_name)
        if pricing is None:
            logging.warning(
                "Model necunoscut %s; se foloseste modelul implicit %s",
                model_name,
                self.default_model,
            )
            pricing = self.pricing[self.default_model]

        cost = Decimal("0")
        if isinstance(tokens, dict):
            for key, value in tokens.items():
                rate_key = self.RATE_KEYS.get(key)
                if not rate_key or value in (None, 0):
                    continue
                cost += _ensure_decimal(value) / Decimal("1000") * pricing[rate_key]
        else:
            cost += _ensure_decimal(tokens) / Decimal("1000") * pricing[self.RATE_KEYS["output"]]

        return cost.quantize(COST_PRECISION, rounding=ROUND_HALF_UP)

    def load_daily_data(self) -> Dict[str, Dict[str, Any]]:
        """Incarca datele zilnice din fisier si migreaza formatul vechi."""
        try:
            with open(self.cost_file, "r", encoding="utf-8") as handler:
                raw_data = json.load(handler)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as exc:
            logging.error("Fisier de costuri corupt: %s", exc)
            return {}

        migrated: Dict[str, Dict[str, Any]] = {}
        for key, entry in raw_data.items():
            cost_value = entry.get("cost", 0)
            migrated[key] = {
                "tokens": int(entry.get("tokens", 0)),
                "cost": _ensure_decimal(cost_value),
                "requests": int(entry.get("requests", 0)),
            }
        return migrated

    def save_daily_data(self, data: Mapping[str, Mapping[str, Any]]) -> None:
        """Salveaza datele zilnice in format compatibil JSON."""
        serializable: Dict[str, Dict[str, Any]] = {}
        for key, entry in data.items():
            cost_decimal = _ensure_decimal(entry.get("cost", Decimal("0")))
            serializable[key] = {
                "tokens": int(entry.get("tokens", 0)),
                "cost": str(cost_decimal),
                "requests": int(entry.get("requests", 0)),
            }
        with open(self.cost_file, "w", encoding="utf-8") as handler:
            json.dump(serializable, handler, ensure_ascii=False, indent=2)

    def get_daily_stats(self) -> Dict[str, Any]:
        """Returneaza sumarul zilei curente."""
        data = self.load_daily_data()
        today_key = datetime.now().strftime(DATE_FORMAT)
        entry = data.get(today_key, {"tokens": 0, "cost": Decimal("0"), "requests": 0})
        return {
            "tokens": entry.get("tokens", 0),
            "cost": _ensure_decimal(entry.get("cost", Decimal("0"))),
            "requests": entry.get("requests", 0),
        }

    def perform_daily_maintenance(self) -> None:
        """Ruleaza curatarea istoricului si resalveaza datele."""
        data = self.load_daily_data()
        self._cleanup_history(data)
        self.save_daily_data(data)

    def _cleanup_history(self, data: Dict[str, Dict[str, Any]]) -> None:
        if self.retention_days <= 0:
            return
        threshold = datetime.now().date() - timedelta(days=self.retention_days)
        for key in list(data.keys()):
            try:
                day = datetime.strptime(key, DATE_FORMAT).date()
            except ValueError:
                logging.warning("Format data necunoscut in cost file: %s", key)
                continue
            if day < threshold:
                logging.debug("Sterg inregistrarea veche de costuri pentru %s", key)
                data.pop(key, None)

    @staticmethod
    def _total_tokens(tokens: Any) -> int:
        if isinstance(tokens, dict):
            return int(sum(int(value) for value in tokens.values()))
        return int(tokens)


# Instanta globala
cost_monitor = CostMonitor()
