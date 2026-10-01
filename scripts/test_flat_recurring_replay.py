"""Boundary tests for the published, synthetic flat recurring invoice example."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.flat_recurring_replay import InputError, evaluate


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "billing-flat-recurring-v1.json"


class FlatRecurringReplayTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_reported_case_is_a_mismatch(self):
        result = evaluate(self.case)
        self.assertEqual(result["verdict"], "MISMATCH")
        self.assertEqual(result["expected_amount"], "150.00")
        self.assertEqual(result["observed_amount"], "50.00")
        self.assertEqual(result["difference"], "100.00")
        self.assertEqual(result["catalog_effective_at"], "2026-07-18T10:00:00Z")

    def test_matching_amount_and_period_is_not_a_catch(self):
        self.case["observed"]["amount"] = "150.00"
        self.assertEqual(evaluate(self.case)["verdict"], "MATCH")

    def test_wrong_period_is_not_a_match_even_with_correct_amount(self):
        self.case["observed"]["amount"] = "150.00"
        self.case["observed"]["period_end"] = "2026-10-01T10:00:01Z"
        self.assertEqual(evaluate(self.case)["verdict"], "MISMATCH")

    def test_catalog_input_order_does_not_select_the_old_price(self):
        self.case["catalog_versions"].reverse()
        self.assertEqual(evaluate(self.case)["expected_amount"], "150.00")

    def test_empty_eligible_catalog_refuses(self):
        self.case["catalog_versions"] = []
        with self.assertRaises(InputError):
            evaluate(self.case)

    def test_unknown_rule_refuses(self):
        self.case["approved_rule"] = "any-price-is-okay"
        with self.assertRaises(InputError):
            evaluate(self.case)

    def test_usage_or_tax_fields_refuse_instead_of_ignoring_them(self):
        for field in ("usage", "tax"):
            with self.subTest(field=field):
                case = copy.deepcopy(self.case)
                case[field] = "1.00"
                with self.assertRaises(InputError):
                    evaluate(case)

    def test_duplicate_catalog_instant_refuses(self):
        self.case["catalog_versions"].append(copy.deepcopy(self.case["catalog_versions"][-1]))
        with self.assertRaises(InputError):
            evaluate(self.case)

    def test_bad_price_refuses(self):
        self.case["catalog_versions"][-1]["price"] = "NaN"
        with self.assertRaises(InputError):
            evaluate(self.case)

    def test_extreme_price_refuses_with_the_same_input_error(self):
        self.case["catalog_versions"][-1]["price"] = "1e999999999"
        with self.assertRaises(InputError):
            evaluate(self.case)

    def test_cli_refusal_is_nonzero_and_explicit(self):
        self.case["catalog_versions"] = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            path.write_text(json.dumps(self.case), encoding="utf-8")
            run = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "flat_recurring_replay.py"), str(path)],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(run.returncode, 2)
        self.assertIn("REFUSED:", run.stderr)
        self.assertNotIn("MATCH", run.stdout)


if __name__ == "__main__":
    unittest.main()
