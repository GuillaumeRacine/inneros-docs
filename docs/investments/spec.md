# Investments section: specification

Status: **draft for owner review** (design and spec phase only; no app code,
deployment or hosting configuration changes). Tracking: issue #39. Upstream
ledger and returns engine: private Context#151. Corporate card migration tasks:
Context#152.

This repository is public. Like `docs/finance/README.md`, this spec uses generic
or fictional examples only. Real entity names, amounts, company names and the
October 2026 task list live in the private Context repository and in the
deployed private snapshot, never here.

---

## 0. Decisions in one screen

| Decision | Choice |
|---|---|
| Where it lives | New private route `/investments` (and `/api/investments`), a sibling of `/finance` and `/business`. Same Auth.js allowlist, same dynamic/no-store, same Pagefind and export exclusion |
| How data gets in | Reuse the finance pattern: a private Context script builds a validated JSON snapshot, gzip+base64, published as a managed server-side environment value by the existing refresh publisher, then a verified redeploy |
| What the UI computes | Nothing financial. The producer computes every amount, return, rank and diff. The server projection only validates, drops unknown fields and derives display age from `asOf` (the same pattern as `freshness()` in `lib/business-model.mjs`) |
| Task source of truth | **GitHub issues labeled `invest-ops` in the private Context repo** for one-off and blocked items, plus a **month-end run-sheet template** for recurring close steps. Not a tasks CSV and not the personal todo board (section 2.4) |
| Step 1 (shippable now) | Overview + Operations checklist, fed by the real October items. Portfolio, Returns and Allocation render an explicit "waiting on ledger (Context#151)" state |
| Charts | Hand-rolled SVG in the existing CSS-module style, no chart library. A new validated six-slot palette (the current finance allocation colors fail categorical checks; section 4.1) |

---

## 1. Information architecture

One route, six tabs. Each tab answers exactly one question. Tab order follows how
often Gui needs it, not the data model.

| # | Tab | The one question | Primary content | Ships in |
|---|---|---|---|---|
| 01 | **Overview** | *What needs me, and is anything wrong?* | "What needs you" (max 5, ranked), "What changed since last snapshot" (max 5), net worth tile, mark-coverage and freshness strip | Step 1 (net worth tile in waiting state until step 3) |
| 02 | **Operations** | *What is left to close this month, and who owns it?* | Month-end run checklist, one-off tasks, blocked-on-Gui items, done-with-evidence log | Step 1 |
| 03 | **Portfolio** | *What do I own and how much is it worth today?* | Positions table with value, status, as-of and 12-month sparkline; entity and account-type split; mark coverage bar; net worth history | Step 3 |
| 04 | **Returns** | *Is each investment and asset class earning its keep?* | Return by asset class vs benchmark, per-position return table (method-appropriate metric), gross vs net, fee drag, fund J-curves | Step 4 |
| 05 | **Allocation** | *Where should the next dollar go?* | Actual vs target by bucket, concentration, cash drag, return vs the 15% ROIC north star, this month's decision memo (max 3 actions) | Step 5 |
| 06 | **Investor updates** | *Which companies need my attention, and who went quiet?* | Latest digest per holding with direction vs prior update, gone-quiet list, action items (which also flow into Operations) | Step 2 |

Navigation rules:

- The tab bar reuses `.tabs` from the Finance Dashboard (numbered `01`..`06`).
- `/finance` and `/business` gain an "Investments ↗" link in their nav rows.
  The Finance Dashboard's existing "Investments" tab keeps working until step 3,
  then becomes a link to `/investments` (open question 3).
- Each Overview item deep-links to its row in the tab that owns it
  (`/investments?tab=operations#task-<id>`). Deep links are the only cross-tab
  state; there are no filters that persist across tabs.
- Mobile (390px): tabs become a horizontal scroll strip; "What needs you" stays
  first and full width; tables collapse into stacked cards, as in Finance.

### 1.1 Overview design rules (ADHD constraint)

- The first thing on the page is **What needs you**: at most 5 items, ranked by
  the producer, each with one verb, the dollar figure at stake, the deadline,
  the effort in minutes, and one "Open" action. Nothing else competes above it.
- If more than 5 items qualify, the panel says "+N more in Operations", never
  shows them.
- When nothing needs Gui, the panel says so in one line, with the next scheduled
  checkpoint. An empty state is a result, not a gap.
- **What changed** shows only deltas since the previous published snapshot
  (task closed, new blocker, mark refreshed, mark went stale, new investor
  update), max 5, newest first.
- Every number carries a status chip and an as-of date (section 3.3). A number
  without a chip is a spec violation and fails the tests.

---

## 2. Operations checklist model

### 2.1 Three kinds of item

| Kind | Examples (generic) | Where it comes from |
|---|---|---|
| `run_step` | Pull FX and month-end marks; batch 2FA portal session; approve proposed ledger rows; commit and run invariants; publish report and decision memo; reconcile statements; payables and tax balance check | The month-end **run-sheet template**, instantiated once per month |
| `one_off` | Pay a corporate tax balance; give a fund manager new bank details; accept share records on a cap-table platform; upload a tax form to a fund portal; move a batch of vendors to the corporate card; send the accountant a reply | A **GitHub issue** labeled `invest-ops` in the private Context repo |
| `blocked_on_gui` | SMS one-time code for a bank statement download; adding an authenticator secret to the agents' password vault; a ruling the agent cannot make | Either of the above with `blocked_on` set. Rendered in its own group because each one unblocks an agent |

### 2.2 Fields

Every item in the snapshot has the same shape regardless of kind:

| Field | Type | Rule |
|---|---|---|
| `id` | string | Stable. `gh-<issue number>` for issues, `run-<YYYY-MM>-<step key>` for run steps |
| `kind` | enum | `run_step`, `one_off`, `blocked_on_gui` |
| `title` | string | Starts with a verb. Max 120 characters |
| `status` | enum | `open`, `in_progress`, `blocked`, `done`, `done_unverified`, `skipped` |
| `owner` | string | `gui` or `agent:<name>` (for example `agent:cfo-investments`) |
| `due` | date or `asap` or null | Real deadlines only. Never inferred |
| `dollarImpact` | Metric (CAD) or null | Money at stake if it slips: an amount owed, a distribution blocked, interest accruing, a run-rate moved. `basis` text says which |
| `effortMin` | integer or null | Gui's minutes for Gui-owned items, agent wall-clock otherwise |
| `blockedOn` | string or null | `gui-2fa`, `gui-ruling`, `third-party`, `upstream:<issue>` |
| `source` | HTTPS URL | The GitHub issue, or the run-sheet / workflow doc for run steps |
| `closesWhen` | string | The evidence that closes it, stated up front (for example "Payment confirmation saved and the tax account balance reads zero") |
| `evidence` | HTTPS URL or null | Required for `done`. A closed item without evidence is shown as `done_unverified` |
| `group` | string | Display group: `Month-end close`, `Investor actions`, `Tax and statements`, `Corporate card migration`, `Blocked on you` |
| `rank` | integer or null | Producer-computed (section 2.5). Only Gui-owned open or blocked items are ranked |
| `whyRanked` | string | One line, for example "Overdue · $ at stake · 15 min" |

### 2.3 Recurring month-end steps (run-sheet template)

The template lives in the private Context repo next to the investment scripts
(proposed `config/invest/run_sheet.yaml`) and is generated from two existing
documents: the monthly investment run design (run-sheet steps 0-7) and the
personal end-of-month workflow (phases 1-9). Each template step has `key`,
`title`, `owner`, `dueBusinessDay` (relative to month end), `effortMin`,
`closesWhen` and an `evidenceProbe`.

| Group | Steps | Evidence probe (auto-close) |
|---|---|---|
| Investment run | 0 scheduled collector posted · 1 `pull` (FX, crypto equity, bank cash and debt, statement sweep) · 2 batched 2FA portal session · 3 `propose` rows · 4 approve · 5 `commit` + invariants · 6 report + decision memo · 7 lookback line | Run artifact exists for the month (`sources.json`, `proposed_rows.csv`, ledger commit, `returns.json`, report path), invariants passed |
| Finance close | Bank and card refresh · statement downloads per account · payables and tax-balance check · cash-flow snapshot | Statement present for each expected account-month (reuses the Finance Dashboard statement coverage) |
| Hygiene (collapsed by default) | Credit check · subscription audit · rental property month close | Manual check only |

Instantiation: the producer creates `run-<YYYY-MM>-<key>` items on business day 1
of the next month. Probes close steps automatically with the artifact as evidence.
Steps without a probe are closed by the agent command `/cfo invest check <key>
--evidence <url>`, which appends to `runs/<YYYY-MM>/checklist.json`. That file is
curated state, so it gets the same durability as the ledger (committed if
Context#151 ruling 7 passes).

Late fund marks: per the run design, a step reopens when a superseding row lands
before business day 10. The Overview "What changed" then shows "Fund mark
arrived, returns re-run".

### 2.4 Source of truth for tasks: recommendation

**Recommended: GitHub issues labeled `invest-ops` in the private Context repo for
one-off and blocked items, and the run-sheet template for recurring steps.** The
dashboard is a read-only view of both.

| Option | For | Against | Verdict |
|---|---|---|---|
| **GitHub issues + labels (private Context repo)** | Already the mandatory coordination surface for agents on every model. Durable, auditable timeline. Closing with an evidence comment matches the PROOF rule. Agents already have `gh`. Private repo, so amounts and names can live in the body | Structured fields need a convention (fenced YAML block in the body). One issue per recurring month-end step would be noise | **Choose, for one-off and blocked items** |
| Tasks CSV next to the ledger | Diffable, structured, sits beside the data | A new list that only this dashboard reads. No timeline, no comments, no notifications. Agents would coordinate on issues anyway, so the CSV drifts from them | Reject. It would be a second competing todo system |
| Personal todo board (GitHub Projects "Life OS") | Already Gui's personal action surface | Hard caps (Up Next 5, In Progress 2, combined action items 5) are deliberate, and a month-end close alone has about 15 steps. Life-wide scope, not finance-specific. Recent items on that board show capture failures, so it is not a reliable feed today | Reject as source. Allowed as a one-way **promotion target**: the top-ranked Gui-owned item may be promoted with a link back to its issue. The dashboard never writes there |

Why the recurring steps are a template and not issues: they repeat every month,
close on artifact evidence and are owned mostly by agents. Thirty issues a month
would bury the five that need judgment.

Issue convention (body block, parsed by the producer):

```yaml
invest_ops:
  owner: gui                 # or agent:cfo-investments
  due: 2026-10-10            # or asap, or omit
  dollar_impact_cad: 12000   # omit if unknown; never guess
  impact_basis: "Distributions held until bank details are confirmed"
  impact_status: estimated   # confirmed | estimated
  effort_min: 15
  blocked_on: gui-2fa        # optional
  group: Investor actions
  closes_when: "Manager confirms new bank details in writing"
```

Labels: `invest-ops` (required), plus the existing `blocked` and `priority:*`
labels and the `type:*` / `status:*` labels the Context repo already requires.
Status mapping: open → `open`; open with `blocked` label → `blocked`; closed as
completed with a closing comment containing `evidence: <https url>` → `done`;
closed as completed without it → `done_unverified`; closed as not planned →
`skipped`.

Migration note: the Finance Dashboard's `tasks` table ("Obligations") is
currently written by hard-coded lists in the Context finance sync scripts. A
follow-up (not part of this issue) moves those into the same issue convention
with a `finance-ops` label, so there is one task mechanism across both sections.

### 2.5 Ranking (producer-side, deterministic)

Candidates: Gui-owned items with status `open` or `blocked`, plus `blocked_on_gui`
items, plus data alarms the producer raises (a mark gone stale on a position
worth more than 5% of the financial portfolio; mark coverage under 80%).

Sort key, in order:

1. Urgency tier: overdue → due within 7 days or `asap` → due within 30 days → no date.
2. `dollarImpact` descending (unknown sorts last within its tier).
3. `effortMin` ascending (quick wins first among equals).
4. `id` for a stable tie-break.

Top 5 become `attention[]` with `rank` 1-5. The UI renders them in the given
order and never re-sorts. `whyRanked` makes the rule visible. (Open question 2.)

---

## 3. Data contract

### 3.1 Pipeline (reuses the finance pattern)

```
private Context repo                                      public superagents app
──────────────────────────────────────────────            ─────────────────────────────
GitHub issues (label invest-ops) ─┐
run_sheet.yaml + runs/YYYY-MM/ ───┤
ledger CSVs + runs/YYYY-MM/       ├─► scripts/invest/      ┌─► INVESTMENTS_SNAPSHOT_GZIP_BASE64
  returns.json (Context#151)      │   dashboard_snapshot.py│   (managed, server-only env)
investor digest JSON sidecar ─────┘   validates, ranks,    │          │
                                      diffs vs previous ───┘          ▼
                                      snapshot.json/.b64     lib/investments-data.ts
                                             │               (allowlist recheck, then
                                             ▼                readGzipSnapshot + project)
                       finance_dashboard_refresh.py                   │
                       (extended: publishes both values,              ▼
                        one verified redeploy, change-only)   /investments, /api/investments
```

- **Producer:** `scripts/invest/dashboard_snapshot.py` in the private Context
  repo, tests in `scripts/test_invest_dashboard_snapshot.py`. It reads issues
  through the existing `gh` session (no GitHub credential is installed on the
  docs host, same as the Business Dashboard collector).
- **Publisher:** the existing `finance_dashboard_refresh.py` gains a second
  surface. It keeps all current guarantees: anonymous-gate check before and
  after, production must equal reviewed `main`, the payload goes through a
  private temp API input file (never stdin or argv), change-only publication,
  the previous success state is retained on failure. Both values publish in
  **one** redeploy, so the two sections never race each other.
- **Cadence:** no new scheduled job. Publication runs (a) on demand at the end of
  each `/cfo invest` subcommand and after `/cfo invest check`, and (b) as part of
  the existing daily finance refresh, which is change-only and silent.
- **Reader:** factor the gzip transport in `lib/finance-snapshot.mjs` into a
  shared `readGzipSnapshot(value, validate, limits)` used by both sections, so
  the canonical-base64, decompression bound and fail-closed rules exist once.

### 3.2 Size budget and transport limit

The current finance snapshot is about 44 KB encoded, close to its own 48,000-byte
cap. Vercel limits the combined size of a deployment's environment variables
(64 KB per deployment at the time of writing; re-check the current limit in
step 1). Consequences:

- Step 1 investments snapshot budget: **12,000 encoded bytes**, enforced by a test
  and by the producer before publishing. Tasks, the checklist and attention fit
  in about 3-5 KB.
- The ledger-backed snapshot (step 3 onward: positions, 24-36 months of marks,
  sparklines, returns) will not fit beside the finance value. Before step 3,
  both sections move to a private object store read server-side (for example a
  private Vercel Blob store with a server-only read token), keeping the same
  validation and fail-closed behavior. That is a hosting configuration change,
  so it needs Gui's approval (open question 4) and is out of scope for this spec PR.

### 3.3 The Metric object (every number)

```json
{
  "value": 512340.12,
  "unit": "CAD",
  "asOf": "2026-09-30",
  "status": "verified",
  "staleAfterDays": 35,
  "sourceId": "src-fund-a-statements",
  "basis": "statement_nav",
  "note": ""
}
```

- `unit`: `CAD`, `USD` (or another 3-letter code), `pct`, `multiple`, `count`.
- `status`: `verified`, `estimated`, `carry_forward`, `stale`, `unresolved`
  (the ledger's own vocabulary from Context#151).
- `value` may be null. Null renders as "Unknown", never as 0.
- The server projection adds `ageDays` and `freshness` (`current`, `aging`,
  `stale`, `unknown`) from `asOf`, `staleAfterDays` and the request time. That is
  the only derived field. Future `asOf` beyond one day → `unknown`.

### 3.4 Snapshot shape (schema version 1)

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-10-05T17:00:00Z",
  "producer": { "commit": "<context sha>", "ledgerCommit": null, "runMonth": null },
  "baseCurrency": "CAD",
  "sources": [
    { "id": "src-ops-issues", "label": "Operations issues", "url": "https://github.com/<owner>/<private repo>/issues?q=label%3Ainvest-ops",
      "observedAt": "2026-10-05T16:58:00Z", "status": "current", "note": "All open and recently closed invest-ops issues" }
  ],
  "attention": [
    { "itemId": "gh-201", "rank": 1, "whyRanked": "Overdue · $ at stake · 20 min" }
  ],
  "changes": [
    { "at": "2026-10-05T16:58:00Z", "kind": "task_closed", "itemId": "gh-198", "text": "Share record accepted", "evidence": "https://github.com/..." }
  ],
  "operations": {
    "month": "2026-09",
    "progress": { "done": 3, "total": 14 },
    "items": [ { "id": "gh-201", "kind": "one_off", "title": "Pay the corporate tax balance", "status": "open",
                 "owner": "gui", "due": "asap", "dollarImpact": { "value": 48000, "unit": "CAD", "asOf": "2026-06-01", "status": "estimated", "staleAfterDays": 30, "sourceId": "src-ops-issues", "basis": "accountant letter", "note": "plus arrears interest" },
                 "effortMin": 20, "blockedOn": null, "source": "https://github.com/...", "closesWhen": "Payment confirmation saved; account balance reads zero",
                 "evidence": null, "group": "Tax and statements", "rank": 1, "whyRanked": "Overdue · $ at stake · 20 min" } ]
  },
  "netWorth": null,
  "coverage": null,
  "portfolio": null,
  "returns": null,
  "allocation": null,
  "investorUpdates": null
}
```

Null sections render a named waiting state ("Needs the investment ledger,
Context#151") with the dependency link. `progress` is counted by the producer.

Shapes added in later steps (same Metric object throughout):

| Section | Shape (abridged) | Step |
|---|---|---|
| `coverage` | `{ asOf, byStatus: { verified, estimated, carry_forward, stale, unresolved } (Metric pct each), oldestMark: { positionId, asOf }, headlineAllowed: bool }` | 3 |
| `netWorth` | `{ current: Metric, scope: "text: what is in/out", series: [{ month, value: Metric }], correctedFor: ["loan double-count"] }` | 3 |
| `portfolio` | `{ positions: [{ id, name, entity, accountType, assetClass, displayBucket, currency, value: Metric, valueNative: Metric, spark: [{ month, value, status }], liquidity, status }], splits: { byEntity: [...], byAccountType: [...] } }` | 3 |
| `returns` | `{ byClass: [{ bucket, twr12m: Metric, benchmark: { name, twr12m: Metric }, excludedReason }], positions: [{ id, method: "twr"|"xirr"|"moic", net: Metric, gross: Metric, feeTier, feeDragCad: Metric }], funds: [{ id, jcurve: [{ date, cumNetCash: Metric }], tvpi: Metric, dpi: Metric, rvpi: Metric, unfunded: Metric }] }` | 4 |
| `allocation` | `{ buckets: [{ bucket, actualPct: Metric, target: { minPct, targetPct, maxPct } or null, driftPp: Metric }], concentration: { top5Pct, hhi, flags }, cashDrag: Metric, roic: { unlevered: Metric, levered: Metric, northStarPct: 15 }, memo: [{ action, amount: Metric, trigger, rulingAsk }] (max 3) }` | 5 |
| `investorUpdates` | `{ asOf, holdings: [{ id, name, type, latestAt, direction: "up"|"flat"|"down"|"unknown", read, kpis: [{ label, values: [{ date, value, unit }] }], quietDays }], goneQuiet: [ids] }` | 2 |

### 3.5 Validation rules (projection in `lib/investments-model.mjs`)

Mirrors `lib/business-model.mjs` and `lib/finance-model.mjs`:

- `schemaVersion === 1`, else invalid. Unknown fields are dropped, never spread.
- IDs `^[a-z0-9][a-z0-9_-]{0,79}$`, unique per table.
- Links HTTPS only, no embedded credentials. `source` and `evidence` may point
  only to `github.com`, `docs.google.com` or `mail.google.com` hosts (allowlist
  test). The app never fetches them.
- Dates are real `YYYY-MM-DD`; timestamps are ISO-8601.
- Enums are closed. `attention` has at most 5 entries, each referencing an item;
  `changes` at most 20 (UI shows 5); `memo` at most 3.
- An item with status `done` and no `evidence` is downgraded to `done_unverified`.
- Any validation failure → state `invalid`, nothing partial is shown (same as
  Finance).

---

## 4. Charts

All charts are inline SVG components in `app/investments/charts/`, styled through
the CSS module tokens, with no new dependency. Every chart ships with a
hover/focus tooltip, an accessible name, and a `<details>` table view with the
same rows, as the Finance history chart already does.

### 4.1 Palette (validated)

The Finance allocation colors (`#234f45 #83a995 #bbcbbb #cba46e #e2cfab #91a7b2`)
fail as a categorical palette: three are outside the lightness band, all six are
below the chroma floor (they read as gray), and the closest adjacent pair is
under the normal-vision floor. Kept for Finance; not reused here.

New six-slot palette for display buckets, in fixed order, keeping the app's
earthy green-and-ochre family. Validated with the dataviz validator against the
app's own surfaces (adjacent pairs, all checks pass):

| Slot | Bucket | Light (surface `#fbfcf8`) | Dark (surface `#18271f`) |
|---|---|---|---|
| 1 | Public markets | `#1f8466` | `#2f9a7a` |
| 2 | Private funds | `#c47f1a` | `#b87c1c` |
| 3 | Angels | `#4a6fb0` | `#6a8fd6` |
| 4 | Crypto | `#b9533a` | `#d46a4e` |
| 5 | Real estate | `#8b5aa6` | `#a97cc6` |
| 6 | Cash | `#6f8f2a` | `#7f9c3a` |
| — | Other | muted ink token (neutral, not a hue) | muted ink token |

Dark-mode tritan separation for slots 1-2 sits in the 6-8 floor band, so every
bucket is also direct-labeled (secondary encoding). Color follows the bucket,
never its rank or the active filter. Ledger asset classes fold into these six
buckets (public fund + self-directed → Public markets).

Mark status is a state, not an identity: verified = solid mark, estimated = solid
mark with a `~` chip, carry-forward = hollow point, stale = hollow point + dashed
segment + `!` chip, unresolved = no mark and an "Unknown" label. Status chips
always pair an icon with a word.

### 4.2 Per view

| View | Form | Why this form | Rules |
|---|---|---|---|
| Net worth over time (Overview tile, Portfolio) | Single line, month-end points, CAD | One series of change over time | Hollow points for carried months, dashed where stale; no legend (title names it); y-axis starts at a round value below the min, labeled. Mark coverage % sits in a **separate** thin 100% bar per month under it (never a second y-axis) |
| Mark coverage | One horizontal 100% stacked bar (verified → estimated → carried → stale → unresolved), single hue at decreasing lightness, texture on stale | Part-to-whole of one total, state not identity | Direct labels with percentages; headline ROIC hidden when verified + estimated < 80% |
| Allocation vs target | Horizontal bullet rows per bucket: actual bar in bucket color, target min-max as a neutral band, target as a tick, drift in pp as text | Compares one value to a range per category; pies cannot show targets | Before targets are ruled: actual bars only and the label "Targets not set" |
| Returns by class vs benchmark | Horizontal bar per class (trailing 12 months, net) with the benchmark as a tick on the same row; value labels at bar end | Magnitude comparison across categories with a reference | Classes excluded for coverage are shown as a hatched placeholder row "Insufficient marks", not dropped. Negative bars extend left of a zero rule |
| Returns trend | Small multiples, one line per class, shared y-scale | Avoids an 8-line spaghetti chart | Same scale across panels so slopes compare honestly |
| Fund J-curve | Small multiple per fund: cumulative net cash flow line with a zero rule; TVPI and DPI as a second small panel (both multiples, same axis) | The J shape is the point; mixing dollars and multiples would need two axes | Dated at quarter-end `asOf`, not arrival date |
| Per-position sparkline | 12 month-end points, no axes, last point emphasized with its status chip | Trend glanceability inside a table row | Hollow points for carried months; min-max range in the tooltip; never colored by up/down alone |
| Concentration | Ranked horizontal bars, top 5 positions + "Rest" | Ranking | Flag text on any single manager above 25% |
| Fee drag | Not a chart: a two-column table ($ per year, % of assets) per manager | Few values, read precisely | — |

Hero numbers (net worth, open items, mark coverage) are stat tiles reusing
Finance's `.stat` component, each with the status chip and as-of line.

---

## 5. Wireframes (low fidelity)

The Paper design MCP was unreachable during this spec pass (desktop app not
running). Real mockups in Paper are the next step before UI code in step 1.

### 5.1 Overview (desktop)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ SUPER AGENTS / INVESTMENTS                         Private · Read-only       │
│ Investments                                                                  │
│ Snapshot 2026-10-05 13:15 ET · current     Finance ↗  Business ↗  Docs ↗     │
├──────────────────────────────────────────────────────────────────────────────┤
│ 01 Overview | 02 Operations | 03 Portfolio | 04 Returns | 05 Allocation | 06 │
├──────────────────────────────────────────────────────────────────────────────┤
│ WHAT NEEDS YOU                                         5 of 9 · +4 in Ops →  │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │1 Pay the corporate tax balance        ~$48,000 · overdue · 20 min   Open→│ │
│ │  Overdue · $ at stake · 20 min                       estimated · 06-01   │ │
│ │2 Confirm new bank details with Fund A  ~$25,000 held · overdue · 15 min →│ │
│ │3 Upload tax form to Fund B portal      distributions held · asap · 15 min│ │
│ │4 Enter SMS code: bank statements       blocks month close · 5 min  [2FA] │ │
│ │5 Accept share records (2 companies)    $ unknown · since May · 10 min   →│ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
├───────────────────────────────────┬──────────────────────────────────────────┤
│ NET WORTH                         │ WHAT CHANGED (since 2026-10-04)          │
│ Waiting on the investment ledger  │ ✓ Portal access restored (3 of 5)        │
│ (Context#151). No Monarch number  │ + Fund statements pulled through 08-31   │
│ is shown: its loan double-count   │ ! Fund C capital call shown overdue      │
│ makes it wrong.                   │ + 3 investor action items added          │
│ [step 3: line chart + chip]       │ ✓ Card migration plan ready (batch 1)    │
├───────────────────────────────────┴──────────────────────────────────────────┤
│ FRESHNESS   Ops issues ✓ current · Run sheet ✓ Sep · Ledger — not built yet  │
│             Investor digest ✓ 10-05 · Marks: 3 stale (oldest 2025-11-30) !   │
└──────────────────────────────────────────────────────────────────────────────┘
(Amounts above are fictional placeholders, not real records.)
```

### 5.2 Operations checklist (desktop)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 02 / OPERATIONS                 September 2026 close · 3 of 14 done ███░░░░░ │
│ Filter: [All owners ▾] [Open ▾]       Source: invest-ops issues ↗ run sheet ↗│
├──────────────────────────────────────────────────────────────────────────────┤
│ BLOCKED ON YOU (3)                                          unblocks agents  │
│ ! SMS code: bank + RRSP statements      gui · 5 min · blocks steps 1, 3    → │
│ ! Add authenticator secret: Fund B      gui · 5 min · blocks Q2 marks      → │
│ ! 6 design rulings (ledger issue)       gui · 15 min · blocks ledger build → │
├──────────────────────────────────────────────────────────────────────────────┤
│ MONTH-END CLOSE · investment run                       due business day 5    │
│ ✓ 0 Collector posted                    agent · evidence: report ↗           │
│ ✓ 1 Pull FX, crypto, cash, statements   agent · evidence: sources.json ↗     │
│ ○ 2 Batched 2FA portal session          gui · 10 min · BD 3                  │
│ ○ 3 Propose ledger rows                 agent · waits on 2                   │
│ ○ 4 Approve rows                        gui · 5 min                          │
│ ○ 5 Commit + invariants                 agent                                │
│ ○ 6 Report + decision memo              agent                                │
│ ○ 7 Lookback line                       agent                                │
│ MONTH-END CLOSE · finance               ✓ refresh  ○ statements  ○ payables  │
│ ▸ Hygiene (3)                                                                │
├──────────────────────────────────────────────────────────────────────────────┤
│ INVESTOR ACTIONS (6)  · TAX AND STATEMENTS (3) · CARD MIGRATION (3 batches)  │
│ ○ Confirm capital-call cheque cleared   gui · 5 min · ~$3,000 · overdue    → │
│ ○ Decide or pass on follow-on offer     gui · 10 min · likely closed       → │
│ ○ Card migration batch 1 (20 vendors)   agent+gui · ~$1,500/mo moved · 45m → │
│   closes when: next billing cycle charges the corporate card                 │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▸ Done with evidence (12)   ▸ Done without evidence (1) !                    │
└──────────────────────────────────────────────────────────────────────────────┘
(Fictional placeholders.)
```

Mobile (390px): each row becomes a card: title, then one meta line (owner ·
minutes · $ · due), then the status chip and "Open ↗". Group headers stay sticky.

---

## 6. Build plan

Every PR follows the repo gate: `npm run check`, `npm run build`, the
authorization matrix, desktop/390px/768px browser checks, dark mode, then the
GitHub, deploy and authenticated-readback loop. Public fixtures are fictional.

| # | PR | Repo | Scope | Tests | Blocked on |
|---|---|---|---|---|---|
| **1a** | Model + reader | superagents | `lib/investments-model.mjs` (schema v1, projection, Metric, freshness), shared `readGzipSnapshot` extracted from `finance-snapshot.mjs`, `lib/investments-data.ts` with allowlist recheck, `/api/investments` | `scripts/test-investments.mjs` (`npm run test:investments`, wired into `check`): valid/invalid/unknown-field drop, max 5 attention, UI-order = producer rank, done-without-evidence downgrade, link host allowlist, 12,000-byte budget, invalid compressed value fails closed; finance tests stay green after the refactor | Nothing |
| **1b** | Overview + Operations UI | superagents | `app/investments/page.tsx` + client view, tabs, waiting states for tabs 03-06, nav links from `/finance` and `/business`, `_meta.js` entry, Pagefind/export exclusion | `scripts/verify-investments.mjs` (copy of `verify-finance.mjs`: allowed, missing, invalid, expired, disallowed sessions for HTML/API/RSC; no-store; sentinel absent from build output); `verify-investments-ui.mjs` screenshots at 390/768/1280 light and dark; persona pass on "find the one thing to do now" | Paper mockup approval |
| **1c** | Producer + seed | Context (private) | `scripts/invest/dashboard_snapshot.py`, `config/invest/run_sheet.yaml`, `invest-ops` label, October items opened as issues with the YAML block, publisher extension in `finance_dashboard_refresh.py` (two values, one redeploy) | `test_invest_dashboard_snapshot.py`: YAML parsing, ranking order on fixed fixtures, run-sheet instantiation for a given month, probe auto-close, diff vs previous, byte budget; refresh tests extended for two surfaces and partial failure (finance publish must not be blocked by an invalid investments snapshot) | Nothing. Activation needs authenticated production readback, as for Finance |
| 2 | Investor updates | both | Digest method emits a JSON sidecar next to the monthly digest; tab 06; digest action items become `invest-ops` issues (deduplicated by holding + action) | Sidecar schema test; direction and quiet-days computed by producer; confidentiality: holdings data only in the private snapshot | Nothing |
| T | Transport move | both | Private object store for both snapshots, same validation and fail-closed; env values removed after verified cutover | Same suites + a cutover test proving the old value is not read once the new source is configured | Open question 4 (hosting change approval) |
| 3 | Portfolio + net worth + coverage | both | Tab 03, net worth tile and chart, coverage bar, sparklines | Producer: coverage invariant (statuses sum to 100%), no Monarch-sourced net worth; UI: hollow/dashed rendering for carried and stale | Context#151 ledger (positions, valuations, fx) + step T |
| 4 | Returns | both | Tab 04, class vs benchmark, trend multiples, J-curves, fee drag | Producer fixtures reconcile to manager-reported returns within 0.25 pp (Context#151 tests); UI shows excluded classes | Context#151 returns engine + benchmark ruling |
| 5 | Allocation + memo | both | Tab 05, bullet rows, concentration, cash drag, ROIC vs 15%, memo | Memo ≤ 3 actions; targets-not-set state | Context#151 target ruling |
| 6 | Cleanup | superagents | Finance "Investments" tab becomes a link; finance tasks move to the `finance-ops` issue convention | Finance regression suite | Open questions 3 and 5 |

**Step 1 = 1a + 1b + 1c**: the Overview and Operations checklist with the real
October pending items (tax balance, fund bank details, fund portal tax form,
capital-call confirmation, cap-table acceptances, card migration batches,
2FA/SMS blockers, accountant reply, design rulings). None of these need the
ledger. The real list with amounts lives in the private tracker, not here.

---

## 7. Open questions (one-line rulings)

1. **Tasks:** one-off and blocked items as `invest-ops` issues in the private Context repo, recurring steps from the run-sheet template, todo board as promotion target only? (Proposed: yes.)
2. **Ranking:** overdue → due ≤ 7 days → due ≤ 30 days → undated, then dollars at stake, then fewest minutes? (Proposed: yes.)
3. **Route:** `/investments` as its own section, with Finance's "Investments" tab turning into a link once step 3 ships? (Proposed: yes.)
4. **Transport:** before step 3, move both snapshots from environment values to a private object store read server-side? (Proposed: yes; it is a hosting change you approve at that point.)
5. **Net worth:** the Investments Overview shows the one net-worth number (ledger-based, loan double-count corrected), and Finance stops showing its own once step 3 ships? (Proposed: yes.)
