---
allowed-tools: Read Write Edit Grep Glob Bash WebSearch WebFetch TaskCreate TaskUpdate mcp__osint-db__query_db
name: hamakom-weekly-lineup
description: >-
  Builds Dor's interactive WEEKLY LINEUP (ליינאפ שבועי) for "המקום הכי חם בגיהנום" — a
  seven-day calendar (ראשון→שבת) that places, on each day, what was PUBLISHED and what is still
  in-progress but PLANNED to publish this week. It reads the live Notion "Investigations" database
  (so it relies on the daily evening sync having already updated it). Use this skill whenever Dor asks
  for "ליינאפ", "ליינאפ שבועי", "לוח שבועי", "מה פורסם השבוע ומה מתוכנן", "תכין לי את השבוע",
  a weekly board/calendar of articles, or any time he wants to see the week's publishing plan at a
  glance. Produce a live, re-openable interactive view, not a static text list.
---

# Weekly lineup — interactive calendar from Notion

This builds an interactive seven-day board of the editorial week, sourced from the **Investigations**
database. It is meant to be run *after* the `hamakom-investigations-sync` job has refreshed Notion
(published articles logged, leads added), so the lineup reflects reality. If the data looks stale,
run the sync first (or tell Dor to).

## What the week means

The Israeli editorial week is **Sunday → Saturday**. Compute the current week's Sunday from today, and
the Saturday six days later. Everything is bucketed by the `תאריך פרסום` (publication date) property.

Two kinds of items belong on the board:
- **פורסם** — Status `פורסם`, date within the week → "what went out", on its day.
- **בעבודה / מתוכנן** — any non-archive in-progress status (`רעיון`, `איסוף`, `תחקיר`, `כתיבה`,
  `עריכה`, `מוכן לפרסום`) whose `תאריך פרסום` falls within the week → "planned to publish this week".

Skip `ארכיון`. Items with no `תאריך פרסום` are undated ideas — they don't sit on a specific day, so
leave them off the calendar (optionally list them in a small "ללא תאריך" tray).

## How to pull the data

Query the Investigations "תחקירים" table view, which exposes every needed property
(`Name`, `Status`, `כתב/ת`, `סוג`, `תאריך פרסום`, `url`):

- view_url: `https://www.notion.so/51e84ef1acde4109807e99c68a6765c9?v=48f6afd6ea0d4810a762ecc668206efb`
- tool: `notion-query-database-view` on the Notion connector
  (`mcp__d7ee54d7-455a-4c81-8220-bac43154f6cf__notion-query-database-view`)
- paginate with `start_cursor` until `has_more` is false.

Each row gives: `Name`, `Status`, `כתב/ת`, `סוג`, `url`, and the date as `date:תאריך פרסום:start`
(`YYYY-MM-DD`).

## How to deliver it — use the locked template

**Start from `assets/lineup-template.html`** — it is the approved, battle-tested board (Dor signed off
on this exact format). Copy it, adjust the baked-in snapshot to the current week, and ship it as a
**cowork artifact** (`create_artifact` / `update_artifact`, id `hamakom-weekly-lineup`) with these
`mcp_tools`:
- `mcp__d7ee54d7-455a-4c81-8220-bac43154f6cf__notion-query-database-view` (live board data)
- `mcp__d7ee54d7-455a-4c81-8220-bac43154f6cf__notion-update-page` (drag-reschedule, status/writer edits)
- `mcp__d7ee54d7-455a-4c81-8220-bac43154f6cf__notion-create-pages` (the "+ רעיון חדש" quick-add)

Non-negotiables learned the hard way:
- The artifact must be a **complete HTML document with `<meta charset="utf-8">`** — without it Hebrew
  renders as gibberish.
- The layout is **horizontal**: one continuous board, seven day-columns side by side (ראשון rightmost,
  RTL), never collapsing to a vertical list — on narrow screens it scrolls horizontally.
- Parse `callMcpTool` results defensively (object with `results`/`pages`, JSON string, or
  `content[].text`) and keep a baked-in snapshot of the current week as fallback.
- Don't add a reload button — the artifact header has one.

If a live artifact isn't appropriate (e.g. headless in the scheduled job), generate the same template
as a **standalone HTML file** in outputs with the week's data baked in.

## Board behaviour (all present in the template)

- **Week navigation**: ‹ שבוע קודם · השבוע · שבוע הבא › — all rows are loaded once; navigation just
  shifts the 7-day window, so past and future weeks work instantly.
- **Drag & drop**: dragging a card to another day updates `תאריך פרסום` on the real Notion page
  (optimistic UI, revert + toast on failure).
- **Inline edits**: each card has a Status dropdown and a כתב/ת dropdown that write straight to Notion.
- **Quick-add**: the "+ רעיון חדש" button opens a small form (name required; תקציר, כתב/ת, סוג, date
  optional) and creates a real Investigations page with Status=`רעיון`, עורך/ת=Dor, and the marker
  `[נפתח מהליינאפ]` in תקציר. No date → it lives in the leads view, not on the board (never invent dates).
- **Filters & counts** for the three categories.

## Colors — Anthropic brand palette (locked)

Background Ivory `#faf9f5`, ink `#141413`, lines `#e8e6dc`, accent (today / primary button) `#d97757`.
Status mapping — each card gets a colored start-border + pill:
- **פורסם** → green `#788c5d`
- **בעבודה** (איסוף/תחקיר/כתיבה/עריכה/מוכן לפרסום) → blue `#6a9bcc`
- **רעיון** → orange `#d97757`
Sort within a day: פורסם → בעבודה → רעיון. Keep it calm and readable — a glance-tool, not a wall of text.

## Tone of the summary

After building it, give Dor a one-line orientation (how many published this week, how many still planned)
and the link/artifact. Hebrew only, no emojis.
