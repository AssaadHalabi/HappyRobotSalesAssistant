import unittest

from app.calls import build_call_summary


class CallSummaryTest(unittest.TestCase):
    def test_flattens_extract_and_classification(self):
        summary = build_call_summary({
            "call_id": "call-123",
            "extract": {
                "mc_number": "123456",
                "carrier_name": "Blue Ridge Transport",
                "loadboard_rate": "$2,450",
                "final_rate": "2500",
                "negotiation_rounds": 2,
            },
            "classification": {
                "call_outcome": "Booked",
                "carrier_sentiment": "Positive",
            },
        })

        self.assertEqual(summary["call_id"], "call-123")
        self.assertEqual(summary["mc_number"], "123456")
        self.assertEqual(summary["loadboard_rate"], 2450)
        self.assertEqual(summary["final_rate"], 2500)
        self.assertEqual(summary["call_outcome"], "booked")
        self.assertEqual(summary["carrier_sentiment"], "positive")


if __name__ == "__main__":
    unittest.main()
