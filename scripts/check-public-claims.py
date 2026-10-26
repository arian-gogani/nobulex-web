#!/usr/bin/env python3
"""Refuse public claims that outrun the implementation.

Two rules govern every check in this file.

First, a check that cannot run must fail, not pass. Returning success because
the input was missing is the exact defect this repository exists to find in
other people's software. Every "could not be checked" branch below appends an
error and names what went unchecked.

Second, the PASS line may only state what was actually tested. A message that
describes a property ("carries no deployed-prevention claim") while the code
tested two exact English sentences is evidence overstating its coverage, which
is the same defect wearing a green badge.
"""

from pathlib import Path
import html as html_module
import json
import re
import sys


ROOT = Path(__file__).resolve().parents[1]


def unhedged_inline_gateway(page: str) -> str | None:
    """Return an inline-gateway claim that is not hedged as not deployed.

    A literal ban on "Nobulex is now an inline" misses the same claim with
    "now" removed. CSS such as display:inline-flex sits inside tags and is
    stripped before the word window is checked. "not deployed" in the same
    window is the hedge the corrected pages already use.
    """
    plain = re.sub(r"<[^>]+>", " ", page)
    plain = re.sub(r"[^A-Za-z0-9]+", " ", plain).lower()
    pattern = re.compile(r"\binline\b(?:\s+\w+){0,6}\s+gateway\b")
    for match in pattern.finditer(plain):
        start = max(0, match.start() - 80)
        span = plain[start:match.end()]
        if "not deployed" not in span:
            return plain[match.start():match.end()]
    return None


def meta(html: str, key: str) -> str | None:
    """Return a meta tag's content, or None when the field is absent.

    This used to be a single regex requiring name-then-content attribute order
    and a bare ``>`` terminator, and it used to raise AssertionError on a miss.
    Both were defects. A perfectly valid ``<meta content="..." name="description" />``
    made the regex miss, the raise propagated out of main(), and every error
    already queued in the errors list was discarded unprinted: the script died
    reporting one missing field while silently dropping real violations it had
    already found.

    So: attribute order is free, the tag may be self-closing, either quote
    style works, and a miss returns None so the caller records an error and the
    run continues to completion with the full error list intact.
    """
    for tag in re.findall(r"(?is)<meta\b[^>]*>", html):
        if not re.search(
            rf"""(?is)\b(?:name|property)\s*=\s*["']{re.escape(key)}["']""", tag
        ):
            continue
        # The quote character is captured and backreferenced rather than put in
        # a negated class. A class like [^"']* stops at the first quote of
        # either kind, so a double-quoted content value containing an
        # apostrophe ("anyone's production path") would be silently truncated
        # at the apostrophe and the substring checks would run on a fragment.
        match = re.search(r"""(?is)\bcontent\s*=\s*(["'])(.*?)\1""", tag)
        if match:
            return html_module.unescape(match.group(2))
    return None


def read_text(path: Path, errors: list) -> str:
    """Read a required file, or record that its assertions went unchecked.

    Reading directly used to abort main() on the first missing file, with the
    same error-discarding consequence as the old meta(). Returning "" instead
    lets every remaining check run and fail closed, because an empty string
    satisfies none of the required-substring assertions below.
    """
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(
            f"{path.name} could not be read, so every assertion this script "
            f"makes about it is unchecked: {exc}"
        )
        return ""


# --------------------------------------------------------------------------
# Claim-shaped language
# --------------------------------------------------------------------------
# The per-page loop below used to test for two exact English sentences. That is
# a useful regression guard for two specific overclaims that were removed once,
# but it is not a check for overclaiming, and the PASS line used to describe it
# as one. All three of these passed a green run:
#
#   gateway.html            "The gateway is live and blocks real orders."
#   revenue-assurance.html  "We have recovered $4.2M for customers."
#   methodology.html        "Nobulex is deployed in production today."
#
# None of them contains either banned sentence. So there is now a scan for the
# shape of a claim rather than its exact wording, in three families: money
# recovered, present-tense deployment, and customer adoption.
#
# The scan is lexical and therefore approximate. It is tuned to err toward
# flagging, because a false positive costs one sentence rewrite and a false
# negative costs the company's credibility. Two deliberate limits keep it
# honest rather than merely loud:
#
#   Negation scope. This site's whole value is sentences like "not deployed in
#   production" and "Nobody is blocking live orders through Nobulex today". A
#   scan that flagged those would pressure a future editor to delete the
#   disclosures, which is worse than no scan. So a sentence carrying a negation
#   or hedge cue is not flagged, and a short heading-like fragment ("Not a fit
#   yet") carries its negation into the block it governs.
#
#   Sentence confinement. Proximity windows stop at sentence boundaries. The
#   money-and-verb window crossing a full stop is what made "called for $150.
#   The issue reporter says the dry run also returned $50" look like a recovery
#   claim when it is a measurement.
#
# A sentence can still evade this ("There is no doubt Nobulex is deployed in
# production today"). This is a review aid, not a proof.

_BLOCK = (
    r"(?:p|div|li|ul|ol|h[1-6]|section|header|footer|main|article|aside"
    r"|blockquote|figure|figcaption|dt|dd|dl|table|thead|tbody|tr|td|th"
    r"|br|hr|nav|form|label|button|details|summary|pre)"
)

_MONEY = (
    r"(?:\$\s?\d[\d,]*(?:\.\d+)?\s?(?:[KkMmBb]\b|thousand|million|billion)?"
    r"|\d[\d,]*(?:\.\d+)?\s?(?:USD|dollars))"
)

# Verbs that make a money figure a recovery claim on their own.
_RECOVER_STRONG = (
    r"(?:recover(?:ed|s|ing|y|ies)?|recoup(?:ed|s|ing)?|reclaim(?:ed|s|ing)?"
    r"|recaptur(?:ed|es|ing)?|claw(?:ed|s)?\s+back|sav(?:ed|es|ings|ing))"
)

# Verbs that are claim-shaped only when attributed to us or to a beneficiary.
# "the dry run also returned $50" describes an API response, not a recovery.
_RECOVER_WEAK = r"(?:return(?:ed|s)?|found|identif(?:ied|ies)|surfac(?:ed|es))"

_ATTRIBUTION = (
    r"(?:\bwe\b|\bour\b|\bus\b|\bnobulex\b"
    r"|\bthe\s+(?:platform|product|gateway|service)\b"
    r"|\bcustomers?\b|\bclients?\b)"
)

# Filler words an editor inserts or drops without changing what a sentence
# claims. Every pattern below that joins two required words joins them with
# _GAP rather than with \s+, because one filler word is otherwise enough to
# defeat the match. That was not hypothetical: "in production now" was blocked
# and "in production" passed, so deleting four characters shipped the claim.
# Lengthening a literal blocklist does not fix this, since the next rewrite
# only has to differ by one more word. Marking the optional words optional does.
_FILLER = (
    r"(?:now|today|currently|already|still|also|actually|really|fully|truly"
    r"|literally|simply|just|indeed|in\s+fact|of\s+course|at\s+present"
    r"|as\s+of\s+today)"
)

# Required whitespace that may carry any number of filler words inside it.
# Whitespace itself is collapsed to single spaces upstream by claim_sentences,
# so a claim split across source lines matches the same way as a claim on one.
_GAP = rf"\s+(?:{_FILLER}\s+)*"

_CLAIM_RULES: list[tuple[str, re.Pattern]] = []

_CLAIM_RULES += [
    (
        "dollar-recovery claim",
        re.compile(rf"(?i){_MONEY}[^.]{{0,70}}?\b{_RECOVER_STRONG}\b"),
    ),
    (
        "dollar-recovery claim",
        re.compile(rf"(?i)\b{_RECOVER_STRONG}\b[^.]{{0,70}}?{_MONEY}"),
    ),
    (
        "dollar-recovery claim",
        re.compile(
            rf"(?i){_ATTRIBUTION}[^.]{{0,40}}?\b{_RECOVER_WEAK}\b"
            rf"[^.]{{0,40}}?{_MONEY}"
        ),
    ),
    (
        "dollar-recovery claim",
        re.compile(
            rf"(?i)\b{_RECOVER_WEAK}\b[^.]{{0,30}}?{_MONEY}[^.]{{0,30}}?"
            rf"\bfor\s+(?:our\s+)?(?:customers?|clients?|you)\b"
        ),
    ),
]

_CLAIM_RULES += [
    ("present-tense deployment claim", re.compile("(?i)" + pattern))
    for pattern in (
        rf"\b(?:is|are|it's|we're|now){_GAP}(?:live|deployed|in\s+production)\b",
        rf"\bdeployed{_GAP}(?:in|to|into)\s+(?:production|a\s+customer)",
        # This rule required a trailing qualifier, so dropping the single word
        # "now" from "in production now" defeated it and "Nobulex runs in
        # production" shipped. The qualifier stays required here, because an
        # unattributed bare "in production" would flag the site's own FAQ
        # question "Is anyone running this in production?", and the rule below
        # catches the bare form whenever the sentence attributes it to us.
        r"\bin\s+production\s+(?:today|now|with|for|at)\b",
        rf"{_ATTRIBUTION}(?:\s+\w+){{0,3}}?{_GAP}in\s+production\b",
        r"\b(?:run|runs|ran|running)\s+(?:at|in)\s+(?:production|scale)\b",
        r"\b(?:run|runs|ran|running)\s+(?:at|in|for)\s+\S+\s+"
        r"(?:customers|clients|firms)\b",
        r"\blive\s+(?:for|with|at)\s+"
        r"(?:customers|clients|users|firms|production)\b",
        rf"\b(?:blocks?|blocking|stops?|stopping|prevents?|preventing){_GAP}"
        r"(?:real|live|production|actual)\s+\w+",
        r"\bin\s+a\s+customer\s+production\s+path\b",
        rf"\bgoes?{_GAP}live\b",
        r"\bserving\s+(?:production|customers|live)\b",
    )
]

_CLAIM_RULES += [
    ("customer-count or adoption claim", re.compile("(?i)" + pattern))
    for pattern in (
        r"\b\d[\d,]*\+?\s+(?:paying\s+|enterprise\s+|active\s+)?"
        r"(?:customers|clients|subscribers|firms|enterprises|companies"
        r"|teams|users|installs|deployments)\b",
        r"\b(?:dozens|hundreds|thousands|millions)\s+of\s+"
        r"(?:customers|clients|users|firms|companies|teams)\b",
        rf"\btrusted{_GAP}by\b",
        r"\bused\s+by\s+(?:\d|dozens|hundreds|thousands|leading|top)",
        r"\bjoin\s+\d[\d,]*\b",
        r"\bour\s+(?:customers|clients)\s+(?:have|report|save|recovered)\b",
        r"\b(?:customers|clients)\s+(?:include|including)\b",
    )
]

_NEGATION = re.compile(
    r"(?i)(?:\bnot\b|\bnever\b|\bno\b|\bnobody\b|\bnone\b|\bwithout\b"
    r"|\bcannot\b|\bcan't\b|\bisn't\b|\baren't\b|\bwon't\b|\bdoesn't\b"
    r"|\bdon't\b|n't\b|\byet\b|\buntil\b|\bonce\b|\bwould\b|\bwill\b|\bif\b"
    r"|\bbefore\b|\bproposed\b|\bplans?\s+to\b|\bintends?\s+to\b"
    r"|\baims?\s+to\b|\bgoal\b|\brather\s+than\b|\binstead\s+of\b"
    r"|\bshould\b|\bwhen\b|\bseeking\b|\bexcept\b)"
)

# A fragment at most this long with a negation cue in it reads as a heading
# that governs the block beneath it, e.g. "Not a fit yet".
_HEADING_MAX = 60

# Two overclaims were removed from this site once, and the guard then tested
# for the exact English they were removed in: the substrings "a named signer
# attested" and "stops agents from trading on it". A substring blocklist is
# defeated by any rewrite, including ones that change no meaning at all, so
# "stops agents trading on it" and "a named signer has now attested" both
# passed. These are now matched as shapes: required words in order, any
# whitespace between them, filler words optional, and the inflections an editor
# reaches for. They are scanned per sentence through the same negation and
# heading logic as the claim-shape rules, so the site's own disclosures ("No
# named signer attested to any of it") are not flagged. A hard page-wide ban
# would flag those, and a guard that punishes the disclosure is worse than none.
_BANNED_SHAPES: list[tuple[str, re.Pattern]] = [
    (
        "still implies a verified signer identity",
        re.compile(
            rf"(?i)\bnamed{_GAP}signer\b"
            rf"(?:\s+(?:has|have|had|was|were|is|are|been))*"
            rf"{_GAP}attest(?:ed|s|ing|ation)?\b"
        ),
    ),
    (
        "claims deployed prevention rather than intent",
        re.compile(
            rf"(?i)\b(?:stop|stops|stopped|stopping|prevent|prevents"
            rf"|prevented|preventing|block|blocks|blocked|blocking)"
            rf"{_GAP}agents\b(?:\s+(?:from|against))?"
            rf"{_GAP}trad(?:e|es|ed|ing)\b"
        ),
    ),
]


def claim_sentences(page: str) -> list[str]:
    """Visible prose plus meta content values, split into sentences.

    Meta descriptions are public claims too, so they are scanned. Script, style
    and comment contents are not public prose and are removed. Block-level tags
    become sentence breaks so a heading does not run into the paragraph under
    it.
    """
    text = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1\s*>", " ", page)
    text = re.sub(r"(?s)<!--.*?-->", " ", text)
    metas = [
        m.group(2)
        for m in re.finditer(
            r"""(?is)<meta\b[^>]*\bcontent\s*=\s*(["'])(.*?)\1""", text
        )
    ]
    # Source whitespace is collapsed BEFORE block tags become newlines, so the
    # only newlines left are block boundaries. Collapsing afterwards instead
    # meant every line break in the HTML source was also a sentence break, and
    # the published pages wrap prose at about eighty columns. "A named signer\n
    # attested to it" was therefore split into "A named signer" and "attested
    # to it" and matched nothing, so reflowing a paragraph was enough to defeat
    # the scan. Where the source line break fell decided whether a claim was
    # caught, which is not a property any guard should have.
    text = re.sub(r"\s+", " ", text)
    text = re.sub(rf"(?is)</?{_BLOCK}\b[^>]*>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)

    # A period followed by a digit is a decimal point, not a sentence end.
    # Splitting on it blindly cut "We have recovered $4.2M for customers." in
    # half, so the quoted claim in the failure message was truncated to "We
    # have recovered $4". The lookahead keeps decimals intact while still
    # breaking "called for $150. The issue reporter says", which is the split
    # that stops a money figure in one sentence pairing with a verb in the next.
    sentence_break = r"(?:\.(?!\d)|[!?\n])+"
    fragments = re.split(sentence_break, html_module.unescape(text))
    for value in metas:
        fragments.extend(re.split(sentence_break, html_module.unescape(value)))

    return [
        cleaned
        for cleaned in (re.sub(r"\s+", " ", f).strip() for f in fragments)
        if cleaned
    ]


def unhedged_sentences(page: str):
    """Yield sentences carrying no negation or hedge cue of their own.

    A sentence directly under a short negated fragment is also skipped, because
    that fragment reads as a heading governing the block beneath it.
    """
    previous = ""
    for sentence in claim_sentences(page):
        governed = len(previous) <= _HEADING_MAX and _NEGATION.search(previous)
        previous = sentence
        if _NEGATION.search(sentence) or governed:
            continue
        yield sentence


def scan_rules(
    page: str, rules: list[tuple[str, re.Pattern]]
) -> list[tuple[str, str]]:
    """Return (label, sentence) for each unhedged sentence matching a rule."""
    found = []
    for sentence in unhedged_sentences(page):
        for label, pattern in rules:
            if pattern.search(sentence):
                found.append((label, sentence))
                break
    return found


def scan_claims(page: str) -> list[tuple[str, str]]:
    """Return (family, sentence) for each unhedged claim-shaped sentence."""
    return scan_rules(page, _CLAIM_RULES)


def scan_banned(page: str) -> list[tuple[str, str]]:
    """Return (message, sentence) for each reworded removed overclaim."""
    return scan_rules(page, _BANNED_SHAPES)


# --------------------------------------------------------------------------
# Redirect shadowing
# --------------------------------------------------------------------------

def normalize_route(source: object) -> str:
    """Normalize a route so a bare '/' survives.

    The old code did ``str(source).rstrip("/")``, which turns the source "/"
    into "". The homepage route computed from index.html is "/", and "" never
    equals "/", so the homepage subcase of the shadowing check was dead on
    every run: a redirect sending / somewhere else could never be detected.
    """
    text = str(source).strip()
    if not text.startswith("/"):
        text = "/" + text
    return text.rstrip("/") or "/"


_WILDCARD_HINT = re.compile(r"[:*()\[\]{}+?|]")


def wildcard_regex(source: str):
    """Compile a Vercel source pattern to a regex, or None if unconvertible.

    Treating any wildcard as shadowing every route would be simpler, but this
    repository's own vercel.json contains /arena/:path*, /docs/:path* and
    /api/:path*, none of which can match /pilot or /methodology. Flagging those
    would be a false positive, not a finding, and a guard that cries wolf on
    its own correct config gets switched off. So the pattern is converted and
    actually tested against each asserted route, which still catches every
    root-level wildcard form (/:path*, /(.*), /*). An unconvertible pattern
    returns None and the caller fails closed.
    """
    out = []
    i = 0
    try:
        while i < len(source):
            char = source[i]
            if char == ":":
                name = re.match(r":([A-Za-z_][A-Za-z0-9_]*)", source[i:])
                if not name:
                    return None
                i += name.end()
                if i < len(source) and source[i] == "(":
                    depth, start = 0, i
                    while i < len(source):
                        if source[i] == "(":
                            depth += 1
                        elif source[i] == ")":
                            depth -= 1
                            if depth == 0:
                                i += 1
                                break
                        i += 1
                    else:
                        return None
                    out.append("(?:" + source[start + 1:i - 1] + ")")
                    continue
                suffix = source[i] if i < len(source) else ""
                if suffix == "*":
                    out.append(".*")
                    i += 1
                elif suffix == "+":
                    out.append(".+")
                    i += 1
                elif suffix == "?":
                    out.append("[^/]*")
                    i += 1
                else:
                    out.append("[^/]+")
            elif char == "(":
                depth, start = 0, i
                while i < len(source):
                    if source[i] == "(":
                        depth += 1
                    elif source[i] == ")":
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                    i += 1
                else:
                    return None
                out.append("(?:" + source[start + 1:i - 1] + ")")
            elif char == "*":
                out.append(".*")
                i += 1
            else:
                out.append(re.escape(char))
                i += 1
        return re.compile("".join(out) + "/?")
    except re.error:
        return None


def check_shadowing(config_path: Path, asserted_pages: set, errors: list) -> None:
    """Refuse pages this script asserts about that production redirects away.

    pilot.html was once rewritten to say "This is a prior offer", three checks
    were added to guarantee it said so, and a permanent redirect for /pilot
    landed in the same commit. The checks passed while /pilot returned 308 and
    fifteen bytes, so the page asserting its own retirement could not be loaded
    by anyone. The honest reading of that green run was not "the legacy pilot
    page identifies itself as a prior offer" but "a file nobody can reach says
    so".

    The old implementation of this check had an ``if config_path.exists():``
    with no else. Delete or rename vercel.json and the entire check vanished,
    and the PASS line was byte-identical to a sound run. That is the worst
    possible failure mode for a guard: silence indistinguishable from success.
    It now fails closed and names every page left unchecked.
    """
    routes = {}
    for name in sorted(asserted_pages):
        route = "/" + name.removesuffix(".html")
        routes[name] = "/" if route == "/index" else route

    unchecked = ", ".join(f"{name} ({route})" for name, route in routes.items())

    if not config_path.exists():
        errors.append(
            f"{config_path.name} is missing, so redirect shadowing could not "
            f"be checked for any asserted page: {unchecked}"
        )
        return
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        errors.append(
            f"{config_path.name} could not be read or parsed ({exc}), so "
            f"redirect shadowing could not be checked for any asserted page: "
            f"{unchecked}"
        )
        return
    if not isinstance(config, dict):
        errors.append(
            f"{config_path.name} is not a JSON object, so redirect shadowing "
            f"could not be checked for any asserted page: {unchecked}"
        )
        return

    # A redirect, a rewrite and a routes entry all make the file on disk
    # unreachable at its route. Reading only "redirects" meant moving a rule
    # into "rewrites" silently disabled this check.
    literal: dict[str, str] = {}
    wildcards: list[tuple[str, str, object]] = []

    for key in ("redirects", "rewrites", "routes"):
        block = config.get(key)
        if block is None:
            continue
        if not isinstance(block, list):
            errors.append(
                f"{config_path.name} has a {key!r} key that is not a list, so "
                f"shadowing could not be checked for any asserted page: "
                f"{unchecked}"
            )
            continue
        for index, rule in enumerate(block):
            if not isinstance(rule, dict):
                errors.append(
                    f"{config_path.name} {key}[{index}] is not an object, so "
                    f"shadowing could not be checked for any asserted page: "
                    f"{unchecked}"
                )
                continue
            raw = rule.get("source", rule.get("src"))
            if raw is None or not isinstance(raw, (str, int, float)):
                errors.append(
                    f"{config_path.name} {key}[{index}] has no readable "
                    f"source, so shadowing could not be checked for any "
                    f"asserted page: {unchecked}"
                )
                continue
            source = str(raw)
            if _WILDCARD_HINT.search(source):
                compiled = wildcard_regex(source)
                if compiled is None:
                    errors.append(
                        f"{config_path.name} {key}[{index}] source {source!r} "
                        f"could not be interpreted as a route pattern, so "
                        f"shadowing could not be checked for any asserted "
                        f"page: {unchecked}"
                    )
                    continue
                wildcards.append((key, source, compiled))
            else:
                literal.setdefault(normalize_route(source), f"{key}[{index}]")

    for name, route in routes.items():
        where = literal.get(route)
        if where is not None:
            errors.append(
                f"{name} carries assertions in this script but {route} is "
                f"sent elsewhere by vercel.json {where}, so no reader can see "
                f"what is asserted"
            )
        for key, source, compiled in wildcards:
            if compiled.fullmatch(route):
                errors.append(
                    f"{name} carries assertions in this script but vercel.json "
                    f"{key} pattern {source!r} matches {route}, so no reader is "
                    f"guaranteed to see what is asserted"
                )


def main() -> int:
    errors: list[str] = []

    homepage = read_text(ROOT / "index.html", errors)
    methodology = read_text(ROOT / "methodology.html", errors)
    pilot = read_text(ROOT / "pilot.html", errors)
    readme = read_text(ROOT / "README.md", errors)
    package_raw = read_text(ROOT / "package.json", errors)

    # The HTML pages this script makes assertions about. Listed once, here, and
    # used by the redirect-shadowing check at the end. README.md and
    # package.json are not routes and are deliberately absent.
    #
    # This set had drifted from reality in both directions.
    # billing-study-sample.html carries fourteen required-substring assertions
    # and was missing, so a redirect for /billing-study-sample went unnoticed.
    # methodology.html was listed while carrying zero assertions: its contents
    # were read into a variable and discarded, so the page could have said
    # anything. It now carries the assertions below, which is why it stays.
    asserted_pages = {
        "index.html",
        "methodology.html",
        "pilot.html",
        "billing-pilot.html",
        "billing-study-sample.html",
    }

    # The selector used to be '<section class="hero"', with the quote closing
    # immediately after hero. The element is class="hero hero--billing", so it
    # matched nothing, and str.split returns the whole string when the
    # separator is absent. "hero" was therefore every byte from <!DOCTYPE> to
    # the first </section>: 9,021 characters including <head>, every <meta> and
    # the nav.
    #
    # The four assertions below say "first screen" and were checking "somewhere
    # in the first 110 lines". The required copy could have lived only in meta
    # tags while the visible hero said something else, and this would have
    # passed. A check whose scope is wider than its message is a check that can
    # pass for the wrong reason, which is the thing this file exists to catch.
    hero_open = re.search(r'<section\b[^>]*\bclass="[^"]*\bhero\b[^"]*"', homepage)
    if not hero_open:
        errors.append("homepage has no element with a hero class, so the "
                      "first-screen claims could not be checked")
        hero = ""
    else:
        hero = homepage[hero_open.start():].split("</section>", 1)[0]
    if "Billed $50." not in hero or "Expected $150." not in hero:
        errors.append("homepage first screen does not lead with the reproduced billing failure")
    if 'href="/billing-pilot"' not in hero or "Proposed $2,500 study" not in hero:
        errors.append("homepage first screen does not link and scope the proposed billing offer")
    if "The issue reporter says the dry run" not in hero or "Our released-tag H2 test" not in hero:
        errors.append("homepage conflates the reported dry run with our invoice-only reproduction")

    billing_offer = read_text(ROOT / "billing-pilot.html", errors)
    if 'href="/billing-study-sample"' not in billing_offer:
        errors.append("billing offer does not show the synthetic sample deliverable")
    if "For a price change affecting existing subscriptions, what independent artifact" not in billing_offer:
        errors.append("billing offer does not ask the short buyer-fit question")

    revenue_page = read_text(ROOT / "revenue-assurance.html", errors)
    if re.search(r"\bbilling fixes\b[^.]{0,120}\b(?:are|were)\s+merged\b", revenue_page, re.I):
        errors.append(
            "revenue-assurance.html says billing fixes are merged, but the "
            "Kill Bill fixes are still open"
        )
    if not re.search(r"\bbilling fixes\b[^.]{0,120}\bfiled\b[^.]{0,80}\bstill open\b", revenue_page, re.I):
        errors.append(
            "revenue-assurance.html does not distinguish filed, open billing "
            "fixes from merged security and agent-infrastructure work"
        )

    sample_path = ROOT / "billing-study-sample.html"
    if not sample_path.exists():
        errors.append("synthetic billing study sample page is missing")
    else:
        sample = read_text(sample_path, errors)
        for required in (
            "Synthetic sample, not customer work",
            "Expected $150",
            "Observed $50",
            "August 1 to September 1, 2026",
            "current master build was not run",
            'href="https://github.com/killbill/killbill/pull/2320"',
            'href="https://github.com/arian-gogani/nobulex-web/blob/main/scripts/flat_recurring_replay.py"',
            'href="https://github.com/arian-gogani/nobulex-web/blob/main/examples/billing-flat-recurring-v1.json"',
            'href="https://github.com/arian-gogani/nobulex-web/blob/main/scripts/compare_killbill_dry_run.py"',
            "not with a live Kill Bill 0.24 dry-run response or customer data",
        ):
            if required not in sample:
                errors.append(f"billing sample omits verified scope or value: {required}")
        # The upstream issue reporter checked the dry-run endpoint. Our local
        # released-tag H2 reproduction checked generated invoice amounts.
        if "The issue reporter says the dry run" not in sample:
            errors.append("billing sample does not attribute the dry-run observation to the issue reporter")
        if "Our released-tag H2 test" not in sample:
            errors.append("billing sample does not separate our invoice reproduction")
        if "dry run and final invoice in a released-version test" in sample:
            errors.append("billing sample metadata presents the reported dry run as our test")

    for field in ("description", "og:description", "twitter:description"):
        raw = meta(homepage, field)
        if raw is None:
            errors.append(
                f"index.html has no readable {field} metadata field, so "
                f"prototype status could not be checked for it"
            )
            continue
        value = raw.lower()
        if "prototype" not in value:
            errors.append(f"{field} does not identify Nobulex as a prototype")
        if "not deployed" not in value:
            errors.append(f"{field} does not disclose that Nobulex is not deployed")

    # methodology.html was read and thrown away. The variable was assigned at
    # the top of main() and never referenced again, so a fifteen-kilobyte
    # published page carried no content assertions at all and could have said
    # "Nobulex is deployed in production today." with a green run. These three
    # substrings are the page's own deployment-status and signer-identity
    # disclosures, which are the same properties this script enforces
    # elsewhere, so the page is now held to them.
    for required in (
        "not deployed in a customer production path",
        "Nobody is blocking live orders through Nobulex today",
        "there is no persistent issuing identity behind it yet",
    ):
        if required not in methodology:
            errors.append(
                f"methodology.html no longer discloses its measured limits: "
                f"{required}"
            )

    pages = sorted(pth for pth in ROOT.glob("*.html"))
    # This used to be ``assert pages``, which was unreachable: index.html was
    # read unconditionally at the top of main(), so an empty directory raised
    # FileNotFoundError long before the assert. read_text() now records that
    # instead of raising, which makes this reachable, and it records rather
    # than asserts so queued errors still print.
    if not pages:
        errors.append(
            "no published .html pages found, so the per-page claim scan, the "
            "analytics-loader check and the claim-shape scan checked nothing"
        )

    # Every published page, not the two that happened to carry the claim when
    # this was written. Planting "a named signer attested" in index.html was
    # caught and planting the identical sentence in why.html was not, while the
    # script still printed "PASS: public metadata states prototype status and
    # signer limits". A checker that names two files and reports on all of them
    # is the evidence-overstates-coverage defect, which is the thing this
    # repository exists to refuse.
    banned_checked = 0
    analytics_checked = 0
    claim_scanned = 0
    for pth in pages:
        page = read_text(pth, errors)
        banned_checked += 1
        # These two used to be literal substring searches, one of which was
        # case-sensitive while the other was not, so the title-cased "Stops
        # Agents From Trading On It" passed while the lowercase form failed.
        # Case was the smaller problem. A substring search also passed
        # "stops agents trading on it" and "a named signer has now attested",
        # which make the same claim in different words. _BANNED_SHAPES matches
        # the shape instead.
        for message, sentence in scan_banned(page):
            errors.append(f"{pth.name} {message}: {sentence!r}")
        if "nobulex is now an inline" in page.lower():
            errors.append(f"{pth.name} claims the gateway is deployed inline")
        inline_claim = unhedged_inline_gateway(page)
        if inline_claim:
            errors.append(
                f"{pth.name} claims an inline gateway without saying it is "
                f"not deployed: {inline_claim!r}"
            )
        if "nobulex proves" in page.lower():
            errors.append(f"{pth.name} claims proof beyond the measured scope")

        claim_scanned += 1
        for family, sentence in scan_claims(page):
            errors.append(
                f"{pth.name} carries an unverified {family} that needs human "
                f"review or a citation: {sentence!r}"
            )

        if pth.name != "404.html":
            analytics_checked += 1
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

    # This used to be a bare substring search over the whole raw file text,
    # while its failure message named the description field. A retired category
    # in "description" therefore passed as long as the search term survived
    # anywhere else in the file, for example inside a "homepage" URL. The check
    # now parses the JSON and inspects the field the message names.
    package_description = None
    if package_raw:
        try:
            package_data = json.loads(package_raw)
        except ValueError as exc:
            errors.append(
                f"package.json did not parse ({exc}), so the package category "
                f"description could not be checked"
            )
        else:
            if not isinstance(package_data, dict):
                errors.append(
                    "package.json is not a JSON object, so the package "
                    "category description could not be checked"
                )
            else:
                value = package_data.get("description")
                if not isinstance(value, str) or not value.strip():
                    errors.append(
                        "package.json has no description string, so the "
                        "package category description could not be checked"
                    )
                # This condition was the wrong way round. One branch, whose
                # message reads "still describes the retired category", was
                # tested by the ABSENCE of the current category. So the branch
                # never fired on the thing it names: "Nobulex registry
                # prototype and decision-integrity gateway notes" still names
                # the retired register and passed. And it fired on input that
                # contains no retired category at all: the description
                # "Nobulex billing-accuracy research prototype", which is the
                # wording index.html's own meta tags use, was refused with a
                # message asserting a retired category that was not in it.
                # A guard whose message is false about its own input is the
                # evidence-overstates-coverage defect pointed inward.
                #
                # The two properties are separate, so they are now two
                # conditions with two messages, each naming what it tested.
                elif re.search(r"(?i)\b(?:registry|registries|register)\b", value):
                    errors.append(
                        f"package.json description still names the retired "
                        f"registry category: {value!r}"
                    )
                elif "billing-accuracy" not in value.lower():
                    errors.append(
                        f"package.json description does not name the current "
                        f"billing-accuracy category: {value!r}"
                    )
                else:
                    package_description = value

    pilot_description = meta(pilot, "description")
    if pilot_description is None:
        errors.append(
            "pilot.html has no readable description metadata field, so the "
            "archived-offer label could not be checked"
        )
    elif "archived market-data series pilot" not in pilot_description.lower():
        errors.append("legacy pilot metadata does not label the market-data offer as archived")
    if "This is a prior offer." not in pilot:
        errors.append("legacy pilot page does not identify itself as a prior offer")
    if "Request the pilot" in pilot or "subject=Seven-day" in pilot:
        errors.append("legacy pilot page still solicits the retired offer")

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

    # Every assertion above reads a file from disk. None of them can tell
    # whether production serves that file. That gap is what check_shadowing
    # exists to close, and why it fails closed when the config is unreadable.
    check_shadowing(ROOT / "vercel.json", asserted_pages, errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1

    # The sentence names what was actually tested, and nothing wider. It used
    # to say pages "carry no deployed-prevention or verified-signer claim"
    # while testing for two exact English sentences, so it described a property
    # it had not established. The counts are now accumulated by the loop that
    # did the work rather than derived as len(pages) - 1, which hardcoded the
    # existence of exactly one 404.html and reported 11 of 12 pages checked
    # once 404.html was removed.
    print(
        "PASS: %d page(s) carry no unhedged sentence shaped like either "
        "removed overclaim (a named signer attesting, stopping agents from "
        "trading), filler words and whitespace ignored, and contain neither "
        "'Nobulex is now an inline' nor 'Nobulex proves' nor an unhedged "
        "inline-gateway claim; %d page(s) show no "
        "unhedged dollar-recovery, present-tense-deployment or adoption claim, "
        "%d non-404 page(s) load the verified analytics script, index.html "
        "metadata states prototype status, methodology.html discloses its "
        "deployment and signer limits, package.json description names no "
        "retired category and does name "
        "%r, and no asserted route is shadowed in vercel.json: %s"
        % (
            banned_checked,
            claim_scanned,
            analytics_checked,
            package_description,
            ", ".join(pth.name for pth in pages),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
