import os
import unittest

from app.pricing import evaluate_offer_policy


class PricingPolicyTest(unittest.TestCase):
    def setUp(self):
        os.environ["MAX_RATE_ABOVE_LOADBOARD_PCT"] = "8"

    def test_counter_in_early_round(self):
        result = evaluate_offer_policy({
            "loadboard_rate": 2500,
            "offer_rate": 2700,
            "negotiation_round": 1,
        })

        self.assertEqual(result["decision"], "counter")
        self.assertEqual(result["counter_rate"], 2550)

    def test_reject_above_walkaway_on_final_round(self):
        result = evaluate_offer_policy({
            "loadboard_rate": 2500,
            "offer_rate": 2800,
            "negotiation_round": 3,
        })

        self.assertEqual(result["decision"], "reject")
        self.assertEqual(result["walkaway_rate"], 2700)


if __name__ == "__main__":
    unittest.main()
