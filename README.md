# nobulex.com

The website for **Nobulex, the independent reliability registry for agent tools.**

Payment rails prove money moved. Nobulex proves what happened on the other side.

The method, the harness, and the publication gate live in
[**arian-gogani/nobulex-registry**](https://github.com/arian-gogani/nobulex-registry).
This repository is only the site.

---

## The one rule that matters here

**`register.html` is generated. Never edit it by hand.**

It is written by `suite/render_register.py` in the registry repository, which
compiles the page from the records and writes identical bytes to every publish
target in a single build. This repository is one of those targets.

A downstream copy step is a second author, and a second author of that page is
a second chance to publish a name that is under embargo. Records held under
right of reply are kept off that page by construction, not by anybody
remembering to leave them out, and hand editing the file removes the only thing
that makes that true.

To change the register, change the records or `brand/register.template.html` in
the registry repository, then run:

```
python3 suite/render_register.py --publish /path/to/nobulex-web/register.html
```

The generator refuses at build time to write a page carrying a held record's
identifier, a held subject's name, or a verdict token in the embargo block.

### Check it yourself

The page served at `https://nobulex.com/register` should be byte identical to
`brand/register.html` in the registry repository and to `register.html` here.

```
curl -sS https://nobulex.com/register | shasum -a 256
```

`4b8aa822c5883b1022ef1aa1459768a2c024a64674ca823eae5ce24acfcf9051`

If those disagree, something reached the page after the generator produced it.
That value changes whenever the register legitimately changes, which today
means when a record publishes.

---

## Pages

| Path | File | What it is |
|---|---|---|
| `/` | `index.html` | The registry, the category, and the governing test |
| `/register` | `register.html` | **Generated.** The public register |
| `/methodology` | `methodology.html` | How a verdict is decided, and the disclosure rule |
| `/why` | `why.html` | The argument, written to be attacked |
| `/manifesto` | `manifesto.html` | The rules the registry binds itself to |

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

Deploys to Vercel on push to `main`. `vercel.json` also sets
`X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`,
and `X-Frame-Options: SAMEORIGIN`.

---

## House style

No em dashes. No certification language, no trust scores, no dollar figures,
no counts of tests or packages or lines. No present tense about anything that
has not happened yet. The product is a claim that other people's outputs are
not trustworthy, so overclaiming this project's own state is the fastest
available way to make that claim unbelievable.

---

## Corrections

If something on this site is wrong, say so: **nobulex.dev@gmail.com**.

The argument is meant to be attacked, and a correction that lands changes the
page.

---

MIT. See [LICENSE](LICENSE).
