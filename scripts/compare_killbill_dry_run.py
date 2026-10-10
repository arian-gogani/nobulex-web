#!/usr/bin/env python3
"""Compare one caller-exported Kill Bill-shaped dry-run invoice with a declared rule.

This accepts one RECURRING invoice item in USD. The expected amount comes from
the separate catalog fixture, never from the dry-run total. Kill Bill's item
service periods are dates, so this compares period dates only. It neither
contacts Kill Bill nor authenticates the source of either input file.
"""

import copy
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import re
import sys
from uuid import UUID

from scripts.flat_recurring_replay import InputError, evaluate, instant, money


DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def numeric_money(value, location):
    if type(value) not in (int, Decimal):
        raise InputError(f"{location}: expected a JSON number parsed exactly")
    return money(str(value), location)


def service_date(value, location):
    if not isinstance(value, str) or not DATE.fullmatch(value):
        raise InputError(f"{location}: expected YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise InputError(f"{location}: invalid calendar date") from exc
    return parsed.isoformat()


def import_dry_run(case, invoice, expected_subscription_id):
    if not isinstance(case, dict) or not isinstance(invoice, dict):
        raise InputError("expected a case object and invoice object")
    try:
        expected_id = UUID(expected_subscription_id)
    except (TypeError, ValueError, AttributeError) as exc:
        raise InputError("expected_subscription_id: invalid UUID") from exc

    if invoice.get("currency") != "USD" or invoice.get("isParentInvoice") is not False:
        raise InputError("only one non-parent USD invoice is supported")
    if invoice.get("credits") not in (None, []):
        raise InputError("invoice credits are outside this example's scope")
    for field in ("creditAdj", "refundAdj"):
        if field not in invoice or numeric_money(invoice[field], "invoice." + field) != 0:
            raise InputError(f"invoice.{field}: adjustments are outside scope")

    items = invoice.get("items")
    if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
        raise InputError("invoice.items: expected exactly one item")
    item = items[0]
    if item.get("itemType") != "RECURRING" or item.get("childItems") not in (None, []):
        raise InputError("only one flat RECURRING item with no child items is supported")
    if item.get("linkedInvoiceItemId") is not None or item.get("itemDetails") not in (None, ""):
        raise InputError("linked adjustments or detailed item terms are outside scope")
    if item.get("currency") != invoice["currency"]:
        raise InputError("item and invoice currencies disagree")
    try:
        actual_id = UUID(item.get("subscriptionId"))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InputError("item.subscriptionId: invalid UUID") from exc
    if actual_id != expected_id:
        raise InputError("item.subscriptionId differs from the requested subscription")

    amount = numeric_money(item.get("amount"), "item.amount")
    total = numeric_money(invoice.get("amount"), "invoice.amount")
    if amount != total:
        raise InputError("invoice total differs from its sole recurring item")
    if item.get("rate") is not None and numeric_money(item["rate"], "item.rate") != amount:
        raise InputError("item rate differs from amount; proration is outside scope")
    if item.get("quantity") is not None and numeric_money(item["quantity"], "item.quantity") != 1:
        raise InputError("item quantity differs from one; quantity pricing is outside scope")
    start = service_date(item.get("startDate"), "item.startDate")
    end = service_date(item.get("endDate"), "item.endDate")
    if start >= end:
        raise InputError("item service period is not ordered")

    # A Kill Bill invoice item exposes LocalDate, not UTC timestamps. The case
    # supplies the time-of-day for its expected period; only the date is
    # compared here. This is not evidence about time-zone boundaries.
    instant(case.get("period_start"), "period_start")
    instant(case.get("period_end"), "period_end")
    normalized = copy.deepcopy(case)
    normalized["observed"] = {
        "amount": f"{amount:.2f}",
        "period_start": start + case["period_start"][10:],
        "period_end": end + case["period_end"][10:],
        "currency": invoice["currency"],
    }
    result = evaluate(normalized)
    catalog_date = item.get("catalogEffectiveDate")
    result["catalog_version_matches"] = None
    if catalog_date is not None:
        result["catalog_version_matches"] = (
            instant(catalog_date, "item.catalogEffectiveDate")
            == instant(result["catalog_effective_at"], "expected.catalog_effective_at")
        )
        if not result["catalog_version_matches"]:
            result["verdict"] = "MISMATCH"
    result["source"] = "caller-supplied Kill Bill-shaped JSON; authenticity unverified"
    result["scope"] = "one flat recurring USD line; service-period dates only; no credits or adjustments"
    return result


def main():
    if len(sys.argv) != 4:
        print("REFUSED: expected case.json dry-run-invoice.json subscription-uuid", file=sys.stderr)
        return 2
    try:
        case = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        invoice = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"),
                             parse_float=Decimal, parse_int=Decimal)
        result = import_dry_run(case, invoice, sys.argv[3])
    except (OSError, ValueError, TypeError, ArithmeticError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["verdict"] == "MATCH" else 1


if __name__ == "__main__":
    raise SystemExit(main())
