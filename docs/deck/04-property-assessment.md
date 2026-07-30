# Web-property assessment — the two domains

> "Both domains" per the owner's direction: (1) the harperz9.github.io
> portfolio/Project Telos site, and (2) the Flywheel product surface
> (public engine repo + flywheel-desktop + its distribution page).
> Assessed 2026-07-30 from full clones. No registered custom domain exists
> today; behavior-transform.io appears only as a GitHub repository name.

## Property 1 — harperz9.github.io (Project Telos site)

### What it is
72 sitemap pages (87 HTML files), actively maintained (PR #89 merged
2026-07-29), hand-authored on a shared design cascade, deployed from the
private telos-v2 source with a verification gate.

### Strengths (VERIFIED)
- Near-100% metadata hygiene: title/description/OG/Twitter on 71 of 76 root
  pages (the five exceptions are intentional redirect stubs); reproducible
  1200×630 social cards generated from a committed template.
- Tested like a product: ~30 JS unit tests, 8 Python site-contract tests, a
  link-check crawler, a visual contract test, CI.
- Accessibility by rule: skip links, reduced-motion mandates, ARIA labels.
- An honesty discipline with no known peer: a published self-audit
  (SITE-FIX-LIST.md) that caught its own stale versions and over-counts, a
  public correction note ("the honest figure was six"), and a published null
  against its own product's uplift claim. All previously-listed defects were
  re-verified fixed at assessment time.
- Deep evidence library: 4 recorded receipt-backed demonstrations, 14 research
  pages with named falsifiers, 6 DOI'd preprints, a 15-page investor deck.

### Gaps (DRIFT)
- **No custom domain.** Free github.io hosting; zero owned domain authority;
  brand identity split three ways (Zain Dana Harper / Project Telos /
  ZentropyLabs, with a ZentropyLabs-ai GitHub org besides).
- **Zero analytics** (grep-verified: no GA/GTM/Plausible/Umami/Fathom/Clarity).
  The site is unmeasurable — by its own thesis, it cannot make a measured
  claim about itself.
- **No conversion instrument.** No form, calendar, newsletter, or pricing;
  every CTA terminates at a gmail address. The consulting CTA has no landing
  page.
- Homepage is a 4.6 KB JS-dependent shell that leads with a compiler test
  count rather than a value proposition.
- Residue: 5 redirect stubs + legacy directories from the Quanta→Build rename;
  a stale INDEX.json pointing at a dead branch; publications.html was
  nav-orphaned per the fix list (now in the sitemap — verify nav before citing).
- The strongest traction number (Elder ENB: 900k+ downloads, 150k+ unique
  users) is buried in a cover letter.

### Asset verdict
A world-class credibility engine with the commercial layer deliberately (or
by omission) absent. Its value today is evidentiary: it wins the "are these
people real" check instantly. Its unrealized value is everything after that
check — measurement, capture, and a priced next step.

## Property 2 — the Flywheel product surface

### What it is
The public `flywheel` engine repo, the `flywheel-desktop` client (v0.2.2,
releases + Inno Setup installer), and the site's flywheel.html distribution
page.

### Strengths (VERIFIED)
- A real, downloadable product: Windows x64 installer, 20 MB, published
  SHA-256, engine frozen inside (no Python, no PATH). The only one-click
  artifact in the portfolio.
- Supply-chain honesty: releases built from version tags by a public pipeline
  with a gate that refuses mislabeled artifacts; the unsigned-binary caveat is
  published with the hash as the stated substitute.
- OpenAI-compatible gateway (point an existing client at it; receipts arrive
  under the same API) — the lowest-friction adoption path in the system.
- Desktop client codebase enforces its own canon in CI (design tokens, verdict
  mapping, and version truth are unit-tested; files under 300 lines).

### Gaps (DRIFT)
- **The public engine lags the dev engine by ~9×**: 11 API routes and v0.1.0
  in the public repo vs. 96 routes in the local-model dev checkout. The
  desktop client's README describes surfaces (receipts, plugins, memory,
  studio, attest) that the public engine repo does not yet expose — an
  integrity risk for exactly the audience this portfolio courts.
- Distribution is GitHub-releases-only; no product page exists outside the
  portfolio site; Windows-only installer today (macOS/Linux runners exist in
  CI but no shipped artifact).
- No pricing, license clarity beyond FSL-1.1-MIT on the engine, or support
  channel.

### Asset verdict
The product is more real than its public face. The single cheapest
credibility win in the portfolio is a dev→public sync cadence; the second is
a product page with the installer, the hash, and one recorded demo above the
fold.

## Adjacent properties on the shelf

Private repos `harpercompliance-site` and `sendmyletter-site` (both touched
2026-07-15) indicate property experiments beyond the portfolio — the compliance
name in particular aligns with vertical B and the owner's GRC documentation
history. Not assessed (private, out of session scope); noted as existing
assets when a domain strategy is chosen.

## Recommendations (in order of compounding)

1. **One name, one domain.** Pick the commercial identity (ZentropyLabs is the
   publisher of record in the installer) and register one domain; serve the
   site there with github.io as a mirror. Every DOI, receipt, and release
   currently builds authority for a domain the project doesn't own.
2. **Instrument honestly.** Self-hosted, privacy-respecting analytics plus one
   conversion instrument (work-thread form or calendar). This is the site's
   own credo applied to itself: no claim without measurement.
3. **Publish the two vertical pages.** Vertical B assembles from seven
   existing pages; vertical A (sales & marketing) does not exist and is
   greenfield. The deck's Act II is the draft.
4. **Sync the public engine.** Keep the public flywheel repo within one minor
   version of the dev gateway so the desktop README's claims are checkable
   against the code behind them.
5. **Price one thing.** The security/ORCA practice is already revenue-shaped;
   give it (or a receipts pilot for GRC/legal) a package and a number. One
   priced offer converts the evidence library from portfolio into pipeline.
6. **Promote the traction line.** Move the 900k-download graphics record and
   the six-package PyPI roster onto the entry surfaces where a first-time
   visitor forms their judgment.
