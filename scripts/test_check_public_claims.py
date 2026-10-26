#!/usr/bin/env python3
"""Controls for check-public-claims.py.

A control that passes against the broken guard proves nothing. Every control
here was run against the unfixed guard first and recorded, and every one of
them was then re-run against a deliberately sabotaged fix to confirm it reports
a counted assertion failure rather than merely a nonzero exit.

Each control copies the published site into a temporary directory, plants one
violation, points the guard's ROOT at the copy and runs main(). Nothing here
touches the real site.
"""

import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

GUARD = Path(__file__).resolve().parent / "check-public-claims.py"
SITE = GUARD.parent.parent

# Only files the guard reads from the site root. ROOT.glob("*.html") does not
# recurse, so no subdirectory is needed.
COPIED = ("README.md", "package.json", "vercel.json")


def run_guard(root: Path) -> tuple[int, str]:
    """Run the guard with ROOT pointed at a scratch copy of the site."""
    spec = importlib.util.spec_from_file_location("claims_guard", GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = root
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = module.main()
    return code, out.getvalue() + err.getvalue()


class GuardControl(unittest.TestCase):
    """Base class giving each control a private copy of the site."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for page in SITE.glob("*.html"):
            shutil.copy2(page, self.root / page.name)
        for name in COPIED:
            shutil.copy2(SITE / name, self.root / name)
        self.addCleanup(self.tmp.cleanup)

    def plant(self, page: str, snippet: str) -> None:
        """Add visible prose to a published page."""
        target = self.root / page
        text = target.read_text(encoding="utf-8")
        self.assertIn("</body>", text, f"{page} has no body to plant into")
        target.write_text(text.replace("</body>", snippet + "</body>", 1), encoding="utf-8")

    def set_package_description(self, value: str) -> None:
        target = self.root / "package.json"
        data = json.loads(target.read_text(encoding="utf-8"))
        data["description"] = value
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def refuses(self, needle: str) -> str:
        """Assert the guard exits 1 and names the violation."""
        code, out = run_guard(self.root)
        self.assertEqual(code, 1, f"guard passed the planted violation:\n{out}")
        self.assertIn(needle, out)
        return out

    def accepts(self) -> str:
        code, out = run_guard(self.root)
        self.assertEqual(code, 0, f"guard refused a sentence it should allow:\n{out}")
        return out


class PublishedSiteTests(GuardControl):
    """The site as published must still pass, or the rules are too loose."""

    def test_published_site_passes(self):
        self.accepts()

    def test_hedged_disclosures_are_not_flagged(self):
        self.plant(
            "why.html",
            "<p>Nobody is blocking live orders through Nobulex today.</p>"
            "<p>Nobulex is not deployed in production.</p>"
            "<p>Is anyone running this in production?</p>"
            "<p>No named signer attested to any of it.</p>",
        )
        self.accepts()


class RetiredCategoryTests(GuardControl):
    """Defect 1: the condition was the wrong way round.

    The branch whose message reads "still describes the retired category" was
    tested by the ABSENCE of the current category. So a description that still
    named the retired registry passed, and a description that named neither was
    reported as naming the retired one. The branch never fired on the thing it
    names and always fired on correct input.
    """

    def test_retired_registry_category_is_refused(self):
        self.set_package_description(
            "Website for the Nobulex registry prototype and decision-integrity "
            "gateway notes"
        )
        self.refuses("still names the retired registry category")

    def test_missing_current_category_is_not_called_the_retired_one(self):
        self.set_package_description(
            "Website for the Nobulex research prototype"
        )
        code, out = run_guard(self.root)
        self.assertEqual(code, 1, f"guard accepted a description naming no category:\n{out}")
        self.assertNotIn(
            "still names the retired registry category",
            out,
            "guard reports a retired category that the description does not contain",
        )
        self.assertIn("does not name the current", out)

    def test_current_category_still_accepted(self):
        self.set_package_description(
            "Website for Nobulex billing-accuracy research and its prior gateway prototype"
        )
        self.accepts()


class RewordedClaimTests(GuardControl):
    """Defect 2: a substring blocklist loses to trivial rewording."""

    def test_deployment_claim_without_the_word_now_is_refused(self):
        self.plant("why.html", "<p>Nobulex runs in production.</p>")
        self.refuses("present-tense deployment claim")

    def test_deployment_claim_with_the_word_now_is_refused(self):
        self.plant("why.html", "<p>Nobulex runs in production now.</p>")
        self.refuses("present-tense deployment claim")

    def test_gateway_in_production_is_refused(self):
        self.plant("why.html", "<p>The gateway sits in production.</p>")
        self.refuses("present-tense deployment claim")

    def test_literal_signer_phrase_is_refused(self):
        self.plant("why.html", "<p>A named signer attested to it.</p>")
        self.refuses("implies a verified signer identity")

    def test_reworded_signer_phrase_is_refused(self):
        self.plant("why.html", "<p>A named signer has now attested to it.</p>")
        self.refuses("implies a verified signer identity")

    def test_signer_phrase_split_across_lines_is_refused(self):
        self.plant("why.html", "<p>A named signer\n          attested to it.</p>")
        self.refuses("implies a verified signer identity")

    def test_literal_prevention_phrase_is_refused(self):
        self.plant("why.html", "<p>It Stops Agents From Trading On It.</p>")
        self.refuses("claims deployed prevention rather than intent")

    def test_reworded_prevention_phrase_is_refused(self):
        self.plant("why.html", "<p>It stops agents trading on it.</p>")
        self.refuses("claims deployed prevention rather than intent")

    def test_prevention_phrase_with_filler_is_refused(self):
        self.plant("why.html", "<p>It now blocks agents from trading on it.</p>")
        self.refuses("claims deployed prevention rather than intent")

    def test_attested_without_a_named_signer_is_not_flagged(self):
        self.plant(
            "why.html",
            "<p>Cryptography proves who attested to what.</p>",
        )
        self.accepts()


def load_guard():
    """The guard's module, for controls that call its scanners directly."""
    spec = importlib.util.spec_from_file_location("claims_guard_direct", GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FillerWordGapIsLoadBearing(unittest.TestCase):
    r"""One mutation per load-bearing comparison, applied to _GAP.

    Reverting _GAP to a plain r"\s+" broke exactly ONE assertion in the suite
    above. That is thin cover for the comparison the whole fix rests on: the
    original defect was that deleting the four characters of "now" from "in
    production now" shipped the claim. When a single test carries a fix, a
    single careless rewrite of that test retires the protection silently.

    These nine cases call the scanners directly. Five must fire and four must
    stay quiet. The four quiet ones are the half that usually goes unwritten,
    and they are the half that decides whether this guard survives contact
    with the site: a filler-tolerant pattern is one edit away from matching the
    site's own disclosures, and a guard that flags "No named signer attested to
    any of it" gets switched off, after which the true positives stop being
    caught either.
    """

    @classmethod
    def setUpClass(cls):
        cls.guard = load_guard()

    def flagged(self, html):
        return bool(list(self.guard.scan_banned(html))) or bool(
            list(self.guard.scan_claims(html))
        )

    def test_rewordings_that_must_still_be_caught(self):
        for label, html in [
            ("the original bypass, 'now' deleted",
             "<p>Nobulex runs in production.</p>"),
            ("prevention claim with 'from' removed",
             "<p>Nobulex stops agents trading on it.</p>"),
            ("signer claim with filler and a different inflection",
             "<p>A named signer has now attested to the run.</p>"),
            ("two filler words inserted mid-claim",
             "<p>Nobulex is currently already live.</p>"),
            ("adoption claim with filler splitting the pair",
             "<p>Nobulex is trusted already by four firms.</p>"),
        ]:
            with self.subTest(label):
                self.assertTrue(self.flagged(html), label)

    def test_the_sites_own_honest_sentences_must_stay_quiet(self):
        for label, html in [
            ("a disclosure that no signer attested",
             "<p>No named signer attested to any of it.</p>"),
            ("the FAQ asking whether anyone runs it in production",
             "<p>Is anyone running this in production?</p>"),
            ("an explicit negation of both claims",
             "<p>Nobulex is not live and stops no agents trading.</p>"),
            ("a hedged conditional about the future",
             "<p>If it ever goes live, a named signer would attest.</p>"),
        ]:
            with self.subTest(label):
                self.assertFalse(self.flagged(html), label)


if __name__ == "__main__":
    unittest.main()
