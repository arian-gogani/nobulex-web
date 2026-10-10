"""A Kill Bill-shaped export must be imported without dropping invoice lines."""

import copy
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.compare_killbill_dry_run import import_dry_run
from scripts.flat_recurring_replay import InputError


ROOT = Path(__file__).resolve().parents[1]
SUBSCRIPTION = "00000000-0000-4000-8000-000000000001"


class KillBillDryRunImportTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads((ROOT / "examples/billing-flat-recurring-v1.json").read_text())
        self.raw_invoice = (ROOT / "examples/killbill-dry-run-flat-recurring-v1.json").read_text()
        self.invoice = json.loads(
            self.raw_invoice,
            parse_float=Decimal, parse_int=Decimal,
        )

    def compare(self):
        return import_dry_run(self.case, self.invoice, SUBSCRIPTION)

    def test_documented_shape_yields_the_reported_mismatch(self):
        self.assertEqual(self.compare()["expected_amount"], "150.00")
        self.assertEqual(self.compare()["observed_amount"], "50.00")
        self.assertEqual(self.compare()["verdict"], "MISMATCH")

    def test_invoice_amount_overrides_the_case_fixture(self):
        self.invoice["amount"] = Decimal("150.00")
        self.invoice["items"][0]["amount"] = Decimal("150.00")
        self.assertEqual(self.compare()["verdict"], "MATCH")

    def test_wrong_period_is_a_mismatch(self):
        self.invoice["items"][0]["endDate"] = "2026-10-01"
        result = self.compare()
        self.assertEqual(result["verdict"], "MISMATCH")
        self.assertFalse(result["period_matches"])

    def test_additional_charge_refuses_instead_of_ignoring_it(self):
        self.invoice["items"].append({"itemType": "TAX", "amount": Decimal("2")})
        with self.assertRaises(InputError):
            self.compare()

    def test_credit_and_total_disagreement_refuse(self):
        for change in (
            {"creditAdj": Decimal("1")},
            {"refundAdj": Decimal("1")},
            {"credits": [{}]},
            {"amount": Decimal("51")},
        ):
            with self.subTest(change=change):
                invoice = copy.deepcopy(self.invoice)
                invoice.update(change)
                with self.assertRaises(InputError):
                    import_dry_run(self.case, invoice, SUBSCRIPTION)

    def test_wrong_subscription_refuses(self):
        with self.assertRaises(InputError):
            import_dry_run(self.case, self.invoice, "00000000-0000-4000-8000-000000000002")

    def test_missing_or_nonrecurring_line_refuses(self):
        for items in ([], [{**self.invoice["items"][0], "itemType": "USAGE"}]):
            invoice = copy.deepcopy(self.invoice)
            invoice["items"] = items
            with self.assertRaises(InputError):
                import_dry_run(self.case, invoice, SUBSCRIPTION)

    def test_prorated_or_adjusted_line_refuses(self):
        for change in (
            {"rate": Decimal("100.00")},
            {"quantity": Decimal("2")},
            {"linkedInvoiceItemId": "00000000-0000-4000-8000-000000000099"},
            {"itemDetails": "extra terms"},
        ):
            with self.subTest(change=change):
                invoice = copy.deepcopy(self.invoice)
                invoice["items"][0].update(change)
                with self.assertRaises(InputError):
                    import_dry_run(self.case, invoice, SUBSCRIPTION)

    def test_wrong_catalog_version_is_mismatch_even_if_amount_matches(self):
        self.invoice["amount"] = Decimal("150.00")
        self.invoice["items"][0]["amount"] = Decimal("150.00")
        self.invoice["items"][0]["catalogEffectiveDate"] = "2026-07-15T10:00:00Z"
        result = self.compare()
        self.assertEqual(result["verdict"], "MISMATCH")
        self.assertFalse(result["catalog_version_matches"])

    def test_cli_refuses_extra_lines_with_nonzero_exit(self):
        # JSON serializing Decimals as strings would cause an earlier refusal
        # on amount type, without exercising the extra-line guard.
        old = "    }\n  ]"
        self.assertEqual(self.raw_invoice.count(old), 1)
        extra = self.raw_invoice.replace(
            old, '    },\n    {"itemType": "TAX", "amount": 2}\n  ]',
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invoice.json"
            path.write_text(extra)
            run = subprocess.run(
                [sys.executable, "-m", "scripts.compare_killbill_dry_run",
                 str(ROOT / "examples/billing-flat-recurring-v1.json"), str(path), SUBSCRIPTION],
                capture_output=True, text=True, check=False, cwd=ROOT,
            )
        self.assertEqual(run.returncode, 2)
        self.assertIn("REFUSED:", run.stderr)
        self.assertIn("expected exactly one item", run.stderr)
        self.assertNotIn("MATCH", run.stdout)

    def test_cli_match_uses_the_invoice_file_not_the_fixture_amount(self):
        self.assertEqual(self.raw_invoice.count('"amount": 50.00'), 2)
        matched = self.raw_invoice.replace('"amount": 50.00', '"amount": 150.00')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invoice.json"
            path.write_text(matched)
            run = subprocess.run(
                [sys.executable, "-m", "scripts.compare_killbill_dry_run",
                 str(ROOT / "examples/billing-flat-recurring-v1.json"), str(path), SUBSCRIPTION],
                capture_output=True, text=True, check=False, cwd=ROOT,
            )
        self.assertEqual(run.returncode, 0)
        result = json.loads(run.stdout)
        self.assertEqual(result["verdict"], "MATCH")
        self.assertEqual(result["observed_amount"], "150.00")


if __name__ == "__main__":
    unittest.main()
