# Vertical value assessment — two industries, each tool alone and as the system

> Companion to 01-github-profile-analysis.md. The claim discipline of the
> portfolio applies to this document: where a value statement is a projection
> rather than an observed result, it says so.

## The shared premise (why either vertical pays)

Machines made claiming nearly free; checking stayed expensive. Both verticals
below are drowning in AI-produced output whose acceptance currently rests on
confidence. The system's one operation — propose, verify against an external
criterion, keep a re-checkable receipt — is the missing accept path. The
pitch deck already names the wedge categories (originality-verification,
accountable-agent-action, provenance) and is honest that they have no analyst
TAM yet: that is the whitespace, and also the risk.

## Vertical A — sales & marketing (greenfield)

Grep-verified: the current site has zero sales/marketing surface area. No
positioning debt, no incumbent framing to unwind — and no existing proof of
demand either. Everything below is a mapping of shipped capabilities onto
known agency/martech pains, not observed traction.

| Asset | Alone, it is | In this vertical it becomes |
|---|---|---|
| **gather** + snapshot (citation freezing) | research intake with provenance receipts | Claims substantiation: every public sentence traceable to a frozen, hashed source that outlives the live web. Ad-claim defense files that assemble themselves. |
| **forum** | agent orchestration on a replayable causal hash-chain ledger with human gates | Agency accountability: campaign automation the client can re-check instead of trusting a report. A deliverable format no incumbent offers. |
| **flywheel** routing + receipts | one request shape over every provider, observed per-provider scoreboard | AI-spend governance: cost-honest routing, escalation receipts, the first "what did the model spend buy us" ledger. |
| **studio-engine** + telos creative | seeded, replayable generative worlds/brand kits | Reproducible brand systems: same seed, same artifact — campaign creative that is re-derivable, auditable, and provably original-to-seed. |
| **learn** | witnessed courses; every graded step writes a receipt | Enablement proof: onboarding and certification that produce receipts, not completion checkboxes. |
| **mneme** | agent memory where every memory carries provenance | Account knowledge that survives turnover: "who told us this, when, from which document" as a queryable property. |
| **crucible** | falsifiable claim verification | Marketing-claims QA and competitor-claim testing: register the claim, measure it, publish the verdict packet. |

**As the system**: an agency or in-house team runs intake (gather) → brief
verification (crucible) → campaign orchestration (forum) → creative (studio)
→ delivery with receipts (flywheel/desktop), and hands the client one chained
record. The sale is not "AI tools"; it is *defensible delivery*.

**Honest boundaries**: no marketing-specific integrations exist today (no CRM,
no ad-platform connectors — though 17 built-in MCP connectors plus the plugin
registry are the extension path). First proof would need one design-partner
agency.

## Vertical B — provenance-critical, privacy-bound industries (assembled, not built)

The material for this vertical already exists across seven site pages and
several repos; it has never been assembled into one buyer-facing argument.

| Sector | Live requirement | Shipped answer |
|---|---|---|
| **Compliance / model risk (finance)** | Regulators require model origin and lineage to be auditable; incumbent platforms record lineage as editable database rows (site: writing.html; witnessing-spine, DOI'd, steelmans five financial-sector cases). | Merkle-logged receipts with offline inclusion proofs; hash-chained verifiable store with audit tail; attestation binding sign-off to exactly what was reviewed, overclaims tracked. |
| **Legal / e-discovery** | "The summary is not the record." AI summaries entering matters without their sources. | Citation freezing (page bytes fetched, hashed, stored), content-addressed corpora, comprehension gating (a teach-back that pasting the diff cannot pass). |
| **Healthcare administration** | Summaries must keep uncertainty attached (field-guide clinical lane). | Honest nulls as first-class UI; UNVERIFIABLE rendered as loudly as a win; escalation with the failed local attempt on record. |
| **Newsrooms / media** | Every public sentence must find its source (field-guide media lane). | gather → forum → crucible chain; per-block source hashes; tamper caught on re-read (demonstrated in the recorded demos). |
| **Security / red teams (gov, law enforcement, AI labs)** | Authorized adversarial work needs records that hold up afterward, and a lawful-basis gate. | The existing security.html practice + ORCA (v1.0.0, 361 tests, metadata-only engagement workbench). Already revenue-shaped. |
| **Regulated AI operations** | Agent boundaries must be provable, credentials must not travel. | Boundary receipts (raw content never leaves local adapters), capability grants per run, presence-only credentials in the OS keychain, zero telemetry, fully local loop. |

**The privacy story is architectural, not contractual** — this is the
differentiator dense-workflow industries actually buy:
- The desktop client's only base URL is 127.0.0.1:8799; no outbound endpoint
  exists in the codebase.
- Credential *values* never enter the app, the gateway refuses to accept them
  through the marketplace, and the UI shows presence + source only.
- Proofs verify offline: a third party recomputes the Merkle root from the
  leaf with no network, no account, no vendor.
- Write/exec are grants per run; a verify stage without an exec grant reports
  UNVERIFIABLE rather than pretending.

**As the system**: the same loop, pointed at regulated work — intake with
receipts, judgment that fails closed, orchestration with human gates, sign-off
bound to coverage, and an audit trail that a regulator, opposing counsel, or
incident reviewer can re-derive without trusting the operator.

## Value of each tool alone vs. the system

Each lane is deliberately "a full product that also runs alone" — gather,
crucible, index, forum, learn are individually pip-installable with their own
receipts. Alone, each competes in a crowded category on speed/cost and honesty
(the battle map publishes THEY_LEAD rows). Together they occupy compositions
with no incumbent: benchmark-claim escrow, accountable-agent-action,
receipt-carrying creative, the concurrent-desktop agent. The system premium is
the moat; the standalone tools are the doors in.
