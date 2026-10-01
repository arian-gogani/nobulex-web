#!/usr/bin/env python3
"""Compare one synthetic flat recurring invoice with a caller-declared price rule.

This is not a general Kill Bill invoice engine. It handles one subscription,
one flat recurring line and a fully supplied UTC catalog timeline. It does not
fetch or authenticate a catalog, infer policy, calculate tax/usage/credits, or
verify any production invoice. Unsupported input is refused, not passed.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sys


SCHEMA = "nobulex-flat-recurring-replay-v1"
RULE = "latest-effective-before-period-start"
CENT = Decimal("0.01")


class InputError(ValueError):
    """The specified case is absent, malformed, or outside this example's scope."""


def fields(value, expected, location):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise InputError(f"{location}: expected exactly {', '.join(sorted(expected))}")


def instant(value, location):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise InputError(f"{location}: expected a UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError(f"{location}: invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise InputError(f"{location}: expected UTC")
    return parsed.astimezone(timezone.utc)


def money(value, location):
    if not isinstance(value, str):
        raise InputError(f"{location}: use a decimal string, not a number")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise InputError(f"{location}: invalid amount") from exc
    try:
        cents = amount.quantize(CENT)
    except InvalidOperation as exc:
        raise InputError(f"{location}: amount cannot be represented to cents") from exc
    if not amount.is_finite() or amount < 0 or amount != cents:
        raise InputError(f"{location}: expected a finite nonnegative amount to cents")
    return amount


def evaluate(case):
    fields(case, ("schema", "approved_rule", "subscription_started_at",
                  "period_start", "period_end", "currency", "catalog_versions",
                  "observed"), "case")
    if case["schema"] != SCHEMA or case["approved_rule"] != RULE:
        raise InputError("unsupported schema or approved rule")
    if case["currency"] != "USD":
        raise InputError("only this USD fixture is supported")
    started = instant(case["subscription_started_at"], "subscription_started_at")
    start = instant(case["period_start"], "period_start")
    end = instant(case["period_end"], "period_end")
    if not started < start < end:
        raise InputError("subscription and billing period are not ordered")

    versions = case["catalog_versions"]
    if not isinstance(versions, list) or not 1 <= len(versions) <= 1000:
        raise InputError("catalog_versions: expected 1 to 1000 versions")
    candidates = []
    seen = set()
    for index, version in enumerate(versions):
        label = f"catalog_versions[{index}]"
        fields(version, ("effective_at", "effective_for_existing_at", "price"), label)
        effective = instant(version["effective_at"], label + ".effective_at")
        existing = instant(version["effective_for_existing_at"],
                           label + ".effective_for_existing_at")
        price = money(version["price"], label + ".price")
        if effective in seen or existing < effective:
            raise InputError(f"{label}: duplicate effective instant or impossible date order")
        seen.add(effective)
        if effective <= start and existing <= start:
            candidates.append((effective, existing, price, version["effective_at"]))
    if not candidates:
        raise InputError("no eligible catalog version; expected amount is unknown")
    expected = max(candidates, key=lambda row: (row[0], row[1]))

    observed = case["observed"]
    fields(observed, ("amount", "period_start", "period_end", "currency"), "observed")
    amount = money(observed["amount"], "observed.amount")
    observed_start = instant(observed["period_start"], "observed.period_start")
    observed_end = instant(observed["period_end"], "observed.period_end")
    if observed["currency"] != case["currency"] or observed_start >= observed_end:
        raise InputError("observed currency or period is invalid")

    same = amount == expected[2] and observed_start == start and observed_end == end
    return {
        "verdict": "MATCH" if same else "MISMATCH",
        "expected_amount": f"{expected[2]:.2f}",
        "observed_amount": f"{amount:.2f}",
        "difference": f"{expected[2] - amount:.2f}",
        "catalog_effective_at": expected[3],
        "period_matches": observed_start == start and observed_end == end,
        "scope": "synthetic flat recurring fixture only; caller supplied catalog and rule",
    }


def main():
    if len(sys.argv) != 2:
        print("REFUSED: expected one JSON case path", file=sys.stderr)
        return 2
    try:
        case = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        result = evaluate(case)
    except (OSError, ValueError, TypeError, ArithmeticError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["verdict"] == "MATCH" else 1


if __name__ == "__main__":
    raise SystemExit(main())
