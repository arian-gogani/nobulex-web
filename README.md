# nobulex.com

The website for **Nobulex's billing-accuracy research and proposed audit for
usage-based products.**

An earlier decision-integrity gateway prototype evaluates financial evidence
and deterministic policy, returns `PERMIT`, `BLOCK`, or `ESCALATE`, and issues a
receipt. It is not deployed in
production. The historical public register remains available as a prior
direction, but it is not the product described by the homepage.

The method, the harness, and the publication gate live in
[**arian-gogani/nobulex-registry**](https://github.com/arian-gogani/nobulex-registry).
This repository is the site plus bounded billing comparison examples,
not a production billing service.

---

## The register publication boundary

**The records block in `register.html` is generated. Never edit it by hand.**

`suite/render_register.py` in the registry repository compiles the page from
records and can write identical bytes to every publish target in one build.
This repository was one of those targets before later static-page edits made
the full files diverge.

A downstream copy step is a second author and a second chance to publish a name
that is under embargo. Records held under right of reply must be kept off the
records block by the generator, not by someone remembering to leave them out.
Earlier static-page edits already broke whole-file byte identity. This change
corrects only the static direction notice and tagline while the renderer is
blocked: the records block was measured at the same SHA-256 before and after,
`9d8a7c6d7477fdbfa2edda9c9c237d1ad2b8fb662e948aabb896de7c8da33c78`.
That is a narrow exception for a public overclaim, not a way to publish records.

To change the register, change the records or `brand/register.template.html` in
the registry repository, then run:

```
python3 suite/render_register.py --publish /path/to/nobulex-web/register.html
```

The generator refuses at build time to write a page carrying a held record's
identifier, a held subject's name, or a verdict token in the embargo block.

### Check it yourself

The published copy was hand-edited after rendering. Its own records block says
the added analytics and disclosure text prevent byte identity with the
generator's output. Do not regenerate the records block until the held-record
audit passes and the source template and published copy are reconciled.

```
curl -sS https://nobulex.com/register | shasum -a 256
```

The current difference is documented in the served page itself. A clean render
must still pass the registry's publication and embargo checks before replacing
that copy. The earlier whole-page SHA was a historical value, not an expected
hash for today's file.

---

## Pages

| Path | File | What it is |
|---|---|---|
| `/` | `index.html` | Current billing-accuracy research and proposed audit |
| `/register` | `register.html` | Historical register; generated records block with later static-page edits |
| `/methodology` | `methodology.html` | How evidence, policy and receipts are evaluated |
| `/why` | `why.html` | The prior registry argument, retained for the record |
| `/manifesto` | `manifesto.html` | The publication and correction principles |
| `/research-killbill-catalog-replay` | `research-killbill-catalog-replay.html` | A source-backed billing research note, not a customer result |
| `/billing-pilot` | `billing-pilot.html` | Proposed fixed-scope study, not a sold engagement |
| `/billing-study-sample` | `billing-study-sample.html` | Synthetic example of the proposed result |

Everything else is a redirect. `vercel.json` carries permanent redirects from
the pages of the previous site, which was about a different product under the
same name. `_retired/` holds those pages on disk for recovery and is served by
nothing, listed in `robots.txt`, and never committed.

---

## Running it

Static HTML, CSS, and one small JavaScript file. No build step, no framework,
no dependencies at runtime.

```
python3 -m http.server 8000
```

The synthetic billing comparison uses only Python's standard library:

```
python3 scripts/flat_recurring_replay.py examples/billing-flat-recurring-v1.json
python3 -m unittest scripts.test_flat_recurring_replay
```

The published fixture intentionally exits 1 with `MISMATCH`: the caller-supplied
catalog timeline gives $150, while its observed invoice line is $50. `MATCH`
exits 0 and incomplete or unsupported input prints `REFUSED` and exits 2. This
small example neither runs Kill Bill nor authenticates the catalog; it only
evaluates its declared flat-recurring rule for a synthetic case. It is not a
general invoice engine or evidence of customer adoption.

For a JSON invoice shaped like Kill Bill's documented dry-run response, a
second local command imports the single `RECURRING` item before applying the
same caller-declared catalog rule:

```
python3 -m scripts.compare_killbill_dry_run examples/billing-flat-recurring-v1.json examples/killbill-dry-run-flat-recurring-v1.json 00000000-0000-4000-8000-000000000001
```

This published export is **synthetic**, not captured from a Kill Bill server.
Its field layout follows [Kill Bill's documented dry-run invoice example](https://docs.killbill.io/0.20/userguide_subscription).
The importer ignores the case fixture's `observed` object and takes the amount
and service dates from the invoice JSON. It refuses multiple items, credits,
adjustments, a different subscription, and unsupported rate or quantity terms.
Kill Bill exposes service **dates**, not UTC instants, in invoice items, so the
import compares period dates only. If the item supplies a catalog effective
timestamp, it also compares that version with the declared expected version.
The script reads local files, does not contact Kill Bill, does not verify either
input's authenticity, and has **not been tested against a live Kill Bill 0.24
dry-run response**. Its `MISMATCH`, `MATCH`, and `REFUSED` exit codes are 1, 0,
and 2 respectively. Separate files do not prove independent provenance: the
catalog timeline must come from an approved source outside the invoice engine
for the comparison to answer the intended question. The importer does not
validate plan identity, account ownership, or every field in Kill Bill's
response. Keep any real invoice or customer data local.

Deploys to Vercel on push to `main`. `vercel.json` also sets
`X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`,
and `X-Frame-Options: SAMEORIGIN`.

---

## House style

No em dashes. No certification language, no trust scores, no unverified dollar figures,
no counts of tests or packages or lines. No present tense about anything that
has not happened yet. The product is a claim that other people's outputs are
not trustworthy, so overclaiming this project's own state is the fastest
available way to make that claim unbelievable.

---

## Corrections

The homepage's structured data previously identified it as the public register,
and its social preview claimed Nobulex proved what happened beyond payment.
The homepage now identifies itself correctly and describes the current scoped
financial-data suite and fictional offline example. This changes metadata,
not the evidence available or what a verdict establishes.

If something on this site is wrong, say so: **nobulex.dev@gmail.com**.

The argument is meant to be attacked, and a correction that lands changes the
page.

---

MIT. See [LICENSE](LICENSE).
