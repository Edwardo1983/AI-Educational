import json
import tempfile
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import cost_monitor


class StubConfig:
    DEFAULT_MODEL = "model-a"
    MODELS = {
        "model-a": {
            "input_per_1k": Decimal("0.1"),
            "cached_input_per_1k": Decimal("0.01"),
            "output_per_1k": Decimal("0.3"),
        },
        "model-b": {
            "input_per_1k": Decimal("0.2"),
            "cached_input_per_1k": Decimal("0.02"),
            "output_per_1k": Decimal("0.4"),
        },
    }


class CostMonitorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.cost_file = Path(self.temp_dir.name) / "daily_costs.json"
        self.monitor = cost_monitor.CostMonitor(
            cost_file=str(self.cost_file),
            daily_limit_usd=Decimal("5.00"),
            config_cls=StubConfig,
        )

    def test_calculate_cost_with_breakdown(self):
        tokens = {"input": 1000, "cached_input": 500, "output": 2000}
        cost = self.monitor.calculate_cost(tokens, model="model-a")
        expected = (
            Decimal("0.1") * Decimal("1")
            + Decimal("0.01") * Decimal("0.5")
            + Decimal("0.3") * Decimal("2")
        ).quantize(cost_monitor.COST_PRECISION)
        self.assertEqual(cost, expected)

    def test_calculate_cost_unknown_model_fallback(self):
        cost = self.monitor.calculate_cost(1500, model="unknown")
        expected = (Decimal("1500") / Decimal("1000")) * Decimal("0.3")
        self.assertEqual(cost, expected.quantize(cost_monitor.COST_PRECISION))

    def test_log_usage_persists_decimal_costs(self):
        self.assertTrue(self.monitor.log_usage(2000, model="model-a"))
        data = self.monitor.load_daily_data()
        today = datetime.now().strftime(cost_monitor.DATE_FORMAT)
        entry = data[today]
        self.assertEqual(entry["tokens"], 2000)
        self.assertIsInstance(entry["cost"], Decimal)
        self.assertEqual(entry["requests"], 1)

    def test_log_usage_enforces_limit(self):
        # force limit by using small limit
        monitor = cost_monitor.CostMonitor(
            cost_file=str(self.cost_file),
            daily_limit_usd=Decimal("0.01"),
            config_cls=StubConfig,
        )
        allowed = monitor.log_usage(1000, model="model-a")
        self.assertFalse(allowed)

    def test_cleanup_history_removes_old_entries(self):
        stale_date = (datetime.now() - timedelta(days=40)).strftime(cost_monitor.DATE_FORMAT)
        recent_date = datetime.now().strftime(cost_monitor.DATE_FORMAT)
        with open(self.cost_file, "w", encoding="utf-8") as handler:
            json.dump(
                {
                    stale_date: {"tokens": 10, "cost": "0.1", "requests": 1},
                    recent_date: {"tokens": 20, "cost": "0.2", "requests": 1},
                },
                handler,
                ensure_ascii=False,
                indent=2,
            )
        self.monitor.perform_daily_maintenance()
        data = self.monitor.load_daily_data()
        self.assertNotIn(stale_date, data)
        self.assertIn(recent_date, data)

    def test_load_data_migrates_legacy_float(self):
        today = datetime.now().strftime(cost_monitor.DATE_FORMAT)
        with open(self.cost_file, "w", encoding="utf-8") as handler:
            json.dump({today: {"tokens": 5, "cost": 0.5, "requests": 1}}, handler)
        data = self.monitor.load_daily_data()
        self.assertIsInstance(data[today]["cost"], Decimal)


if __name__ == "__main__":
    unittest.main()
