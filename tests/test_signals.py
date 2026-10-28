import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from screener import is_a_share, available_name, macd_signal
import pandas as pd

def sample(prices):
    return [
        {"date": f"{2018 + i // 12:04}-{i % 12 + 1:02}-28", "close": p}
        for i, p in enumerate(prices)
    ]

class SignalsTest(unittest.TestCase):
    def test_universe(self):
        self.assertTrue(is_a_share("sh.600000"))
        self.assertTrue(is_a_share("sz.300001"))
        self.assertFalse(is_a_share("sz.200001"))
        self.assertFalse(is_a_share("sh.000001"))
        self.assertTrue(available_name("贵州茅台"))
        self.assertFalse(available_name("*ST公司"))
        self.assertFalse(available_name("某某退"))

    def test_flat(self):
        self.assertIsNone(macd_signal(sample([10.0] * 90)))

    def test_confirmed_recent_cross(self):
        prices = [36 - .2 * i for i in range(60)] + [24, 27, 30]
        result = macd_signal(sample(prices))
        self.assertIsNotNone(result)
        self.assertEqual(result["months_since_cross"], 1)
        self.assertTrue(result["cross_below_zero"])
        self.assertGreater(result["dif"], result["dea"])

    def test_user_macd_10_22_8(self):
        prices = [36 - .2 * i for i in range(60)] + [24, 27, 30]
        result = macd_signal(sample(prices))
        close = pd.Series(prices, dtype="float64")
        expected_dif = close.ewm(span=10, adjust=False).mean() - close.ewm(span=22, adjust=False).mean()
        expected_dea = expected_dif.ewm(span=8, adjust=False).mean()
        self.assertAlmostEqual(result["dif"], float(expected_dif.iloc[-1]), places=4)
        self.assertAlmostEqual(result["dea"], float(expected_dea.iloc[-1]), places=4)

    def test_old_cross_ignored(self):
        prices = [36 - .2 * i for i in range(60)] + [24, 27, 30, 32, 34, 36, 38]
        self.assertIsNone(macd_signal(sample(prices)))

if __name__ == "__main__":
    unittest.main()
