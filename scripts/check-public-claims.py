#!/usr/bin/env python3
"""Refuse homepage claims that outrun the implementation."""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]


def meta(html: str, key: str) -> str:
    pattern = rf'<meta (?:name|property)="{re.escape(key)}" content="([^"]*)">'
    match = re.search(pattern, html)
    if not match:
        raise AssertionError(f"missing metadata field {key!r}")
    return match.group(1)


def main() -> int:
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    methodology = (ROOT / "methodology.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    package = (ROOT / "package.json").read_text(encoding="utf-8")
    errors = []

    for field in ("description", "og:description", "twitter:description"):
        value = meta(homepage, field).lower()
        if "prototype" not in value:
            errors.append(f"{field} does not identify Nobulex as a prototype")
        if "not deployed" not in value:
            errors.append(f"{field} does not disclose that Nobulex is not deployed")

    for name, page in (("homepage", homepage), ("methodology", methodology)):
        if "a named signer attested" in page.lower():
            errors.append(f"{name} still implies a verified signer identity")

    if "Nobulex stops agents from trading on it" in homepage:
        errors.append("hero claims deployed prevention rather than product intent")

    gateway_status = (
        "The HTTP decision API and Observe Mode wrapper are implemented and "
        "tested locally. They are not deployed"
    )
    if gateway_status not in homepage:
        errors.append("homepage does not state the measured gateway status")

    if "decision-integrity gateway" not in readme[:500].lower():
        errors.append("README still leads with the retired registry category")

    if "decision-integrity" not in package.lower():
        errors.append("package metadata still describes the retired category")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1

    print("PASS: public metadata states prototype status and signer limits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
