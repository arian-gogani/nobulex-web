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
    pilot = (ROOT / "pilot.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    package = (ROOT / "package.json").read_text(encoding="utf-8")
    errors = []

    hero = homepage.split('<section class="hero"', 1)[-1].split('</section>', 1)[0]
    if "Billed $50." not in hero or "Expected $150." not in hero:
        errors.append("homepage first screen does not lead with the reproduced billing failure")
    if 'href="/billing-pilot"' not in hero or "Proposed $2,500 study" not in hero:
        errors.append("homepage first screen does not link and scope the proposed billing offer")

    billing_offer = (ROOT / "billing-pilot.html").read_text(encoding="utf-8")
    if 'href="/billing-study-sample"' not in billing_offer:
        errors.append("billing offer does not show the synthetic sample deliverable")
    if "For a price change affecting existing subscriptions, what independent artifact" not in billing_offer:
        errors.append("billing offer does not ask the short buyer-fit question")
    sample_path = ROOT / "billing-study-sample.html"
    if not sample_path.exists():
        errors.append("synthetic billing study sample page is missing")
    else:
        sample = sample_path.read_text(encoding="utf-8")
        for required in (
            "Synthetic sample, not customer work",
            "Expected $150",
            "Observed $50",
            "August 1 to September 1, 2026",
            "current master build was not run",
            'href="https://github.com/killbill/killbill/pull/2320"',
            'href="https://github.com/arian-gogani/nobulex-web/blob/main/scripts/flat_recurring_replay.py"',
            'href="https://github.com/arian-gogani/nobulex-web/blob/main/examples/billing-flat-recurring-v1.json"',
        ):
            if required not in sample:
                errors.append(f"billing sample omits verified scope or value: {required}")

    for field in ("description", "og:description", "twitter:description"):
        value = meta(homepage, field).lower()
        if "prototype" not in value:
            errors.append(f"{field} does not identify Nobulex as a prototype")
        if "not deployed" not in value:
            errors.append(f"{field} does not disclose that Nobulex is not deployed")

    # Every published page, not the two that happened to carry the claim when
    # this was written. Planting "a named signer attested" in index.html was
    # caught and planting the identical sentence in why.html was not, while the
    # script still printed "PASS: public metadata states prototype status and
    # signer limits". A checker that names two files and reports on all of them
    # is the evidence-overstates-coverage defect, which is the thing this
    # repository exists to refuse.
    pages = sorted(pth for pth in ROOT.glob("*.html"))
    assert pages, "no published pages found to check"
    for pth in pages:
        page = pth.read_text(encoding="utf-8")
        if "a named signer attested" in page.lower():
            errors.append(f"{pth.name} still implies a verified signer identity")
        if "stops agents from trading on it" in page:
            errors.append(f"{pth.name} claims deployed prevention rather than intent")
        if pth.name != "404.html":
            loader = '<script defer src="/_vercel/insights/script.js"></script>'
            if loader not in page:
                errors.append(f"{pth.name} does not load the verified analytics script")

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

    pilot_description = meta(pilot, "description").lower()
    if "market-data series" not in pilot_description:
        errors.append("pilot metadata does not limit the offer to a market-data series")

    pilot_exclusion = (
        "It does not validate the strategy, recommendation, route, order, "
        "or account action."
    )
    if pilot_exclusion not in pilot:
        errors.append("pilot page does not exclude unsupported decision validation")

    if "manually preserved as a regression fixture" not in pilot:
        errors.append("pilot page implies automatic regression-fixture generation")

    for phrase in ("automated-finance data path", "One financial path"):
        if phrase in pilot:
            errors.append(f"pilot page uses overbroad scope phrase: {phrase}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1

    # The sentence names what was actually read. It used to assert a property
    # of "public metadata" while having read two of six pages.
    print("PASS: %d page(s) carry no deployed-prevention or verified-signer "
          "claim, %d non-404 page(s) load the verified analytics script, "
          "and index.html metadata states prototype status: %s"
          % (len(pages), len(pages) - 1,
             ", ".join(pth.name for pth in pages)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
