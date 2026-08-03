---
allowed-tools: Read Write Edit Grep Glob Bash WebSearch WebFetch TaskCreate TaskUpdate mcp__osint-db__query_db
name: hamakom-investigations-sync
description: >-
  Keeps the "המקום הכי חם בגיהנום" (ha-makom.co.il) editorial workflow in sync between the
  live WordPress site and the Notion "Investigations" database. Use this skill WHENEVER a new
  article is published on ha-makom and should be logged in Notion, whenever Dor asks to sync /
  reconcile the site with נושן, and — importantly — ANY time the conversation touches a specific
  ha-makom article (editing, social, follow-up, fact-check, planning): first look up that article's
  אייטם/תחקיר in the Investigations DB, and if it doesn't exist yet, open a new one. Trigger on
  phrases like "כתבה חדשה התפרסמה", "תסנכרן את האתר עם נושן", "תפתח תחקיר ל...", "יש אייטם ל...",
  "מה הסטטוס של הכתבה", a ha-makom.co.il article URL, or any request that implies an article should
  have a matching Notion item. Default to looking up before creating, and never create duplicates.
---

# ha-makom ⇄ Notion Investigations sync

This skill maintains the link between articles published on **ha-makom.co.il** (WordPress) and the
**Investigations** database in Notion, where Dor (editor-in-chief) tracks every אייטם/תחקיר.

There are two modes. Pick based on the request:

- **Sync mode** — a new article was published (or a periodic catch-up). Pull the site, cross-check
  against Notion, and create the missing items as `פורסם`.
- **Lookup-or-create mode** — the conversation is about one specific article. Find its Notion item;
  if none exists, open one. This runs implicitly before almost any article-related task so the work
  is always anchored to a tracked item.

The single most important rule: **dedupe by slug, never create a duplicate.** Dor's team uses
internal nicknames for items, so the same article can hide under an unrecognizable Name. The
reliable key is the article **slug**, which lives inside the `תקציר` field as a `ha-makom.co.il/<slug>/`
URL. Always match on that before creating anything.

## Fixed identifiers

- Investigations **data source** (collection): `11ff4e8f-1d5f-45ed-b1c9-ddea01ba4cb0`
- Investigations **database** page: `51e84ef1acde4109807e99c68a6765c9`
- "תחקירים" table **view** (all rows, all key props): `https://www.notion.so/51e84ef1acde4109807e99c68a6765c9?v=48f6afd6ea0d4810a762ecc668206efb`
- Dor's Notion user id (for `עורך/ת`): `["user://4fb1812b-9d58-4767-b010-651ca6c704df"]`

Property names and allowed values are in `references/reference.md` — read it before writing to Notion,
because the property keys contain slashes (`כתב/ת`, `פלטפורמה/מדיה`) and the date/person fields use
expanded forms that are easy to get wrong.

## Getting the published-article list (the tricky part)

The cooperative `web_fetch` tool **silently strips `_fields` and other underscore params** and returns
an empty body for large WordPress responses. Don't fight it. Instead pull the data through the browser
(Claude in Chrome), where a same-origin `fetch()` honours `_fields` and returns compact JSON:

1. `navigate` any ha-makom page (e.g. `https://www.ha-makom.co.il/robots.txt`).
2. Run `javascript_tool` to fetch and **store the result on `window`**, then read it back in small
   slices — the tool truncates large outputs, so never try to return all rows in one call.

```js
// store, return only a count
(async () => {
  let posts = [];
  for (let pg = 1; pg <= 3; pg++) {
    const r = await fetch(`https://www.ha-makom.co.il/wp-json/wp/v2/posts?after=2026-03-01T00:00:00&per_page=100&page=${pg}&_fields=date,slug,title,author,categories`);
    if (!r.ok) break;
    const d = await r.json(); if (!d.length) break;
    posts = posts.concat(d); if (d.length < 100) break;
  }
  window.__P = posts;
  return 'STORED ' + posts.length;
})()
```

For cover image + dek, fetch a second time with `_fields=slug,excerpt,jetpack_featured_media_url`
(`jetpack_featured_media_url` = the article's hero image; `excerpt.rendered` = the dek / first lines).
Strip HTML and decode entities (`&quot;`→`"`, `&#8211;`→`–`, `&#8217;`→`’`, `&nbsp;`→space, etc.).

Author and category are IDs — map them with the tables in `references/reference.md`.

## Sync mode — step by step

1. **Pull** the published list since the relevant date (browser fetch above). Default lookback: since
   the last item already in Notion, or since the start of the current quarter for a full catch-up.
2. **Load existing items**: query the תחקירים view (`notion-query-database-view`, paginate with
   `start_cursor`). Build the set of slugs already present by extracting `ha-makom.co.il/<slug>` from
   every `תקציר`. Also note items whose Name is a nickname with no slug — match those by topic only
   when confident, otherwise leave them and report.
3. **Diff**: published articles whose slug is not in the existing set are the gaps.
4. **Create** one Notion page per gap in the data source, with:
   - `Name` = article title (decoded)
   - `Status` = `פורסם`
   - `date:תאריך פרסום:start` = publish date (`YYYY-MM-DD`), `date:תאריך פרסום:is_datetime` = 0
   - `סוג` = mapped from category (see reference: דעות→`טור`, מגזין/מראה מקום→`מגזין`, תחקירים→`תחקיר`, else `כתבה קצרה`)
   - `כתב/ת` = mapped from author id — **only** if the author is one of the six staff writers; external
     columnists aren't in the select, so omit the field for them
   - `פלטפורמה/מדיה` = `המקום הכי חם`
   - `עורך/ת` = Dor's user id
   - `תקציר` = `<dek> <article URL>` (the URL is what makes future dedupe work — never omit it)
   - `cover` = the hero image URL (sets the page cover; also gives the board/gallery a thumbnail)
   You can batch up to 100 pages in one `notion-create-pages` call.
5. **Report** to Dor: how many created, and any nickname/no-slug rows you couldn't confidently match
   (those are his call — never invent a publish date for something not found live on the site).

## Lookup-or-create mode

When the task is about a specific article (URL, slug, headline, or a doc/social request that names one):

1. **Identify the slug.** From a URL it's the last path segment. From a headline, search the
   Investigations data source (`notion-search` scoped to the data source, or scan the view) for the
   headline/slug.
2. **If an item exists**, use it — read its Status, כתב/ת, dates, linked Drive docs, and continue the
   real task anchored to it. Surface its Notion link to Dor.
3. **If none exists**, open one. Set `Status` to reflect reality: `פורסם` if it's already live on the
   site (fill date + cover + dek as in sync mode), otherwise the right pipeline stage —
   `רעיון` (lead/idea), `איסוף` (gathering), `כתיבה`, `עריכה`, `מוכן לפרסום`.
4. Never spin up a second item for an article that already has one, even under a nickname. When unsure
   whether two entries are the same article, prefer asking Dor over creating a duplicate.

## Enrichment (cover + dek) and Drive docs

- New `פורסם` items should get a **cover image** and a **dek** in `תקציר` (image = `jetpack_featured_media_url`,
  dek = decoded `excerpt`). This is what makes the Notion board readable at a glance.
- The `Google Drive File` property is a relation to a synced Drive collection, which can't be set by
  value. To link a Drive doc to an item, **insert the Drive link into the page body** (`insert_content`)
  rather than the relation field.

## Housekeeping conventions Dor uses

- Items that turn out to be duplicates or non-articles get renamed with a `DELETE — …` prefix and set
  to `ארכיון`, so they drop out of active views. The connector can't move pages to Notion trash —
  surface the links and let Dor delete them.
- Tasks/notes that landed in Investigations by mistake get **moved** to the Tasks data source
  (`0830baee-2833-49ee-9990-058824e59516`) with `notion-move-pages`.
- A "לידים ורעיונות" view exists; leads/ideas live as `רעיון`/`איסוף` items. (Note: the Notion
  connector's DSL can't apply a status *filter* programmatically — grouping by Status works, filtering
  doesn't, so set that filter in the UI if needed.)

## Leads scan (optional companion step)

Editorial leads are forwarded into Gmail (the "red mail" / contact-form tips). Accounts:
`dor.zommer@30shekel.org`, `dor.zommer@shakuf.co.il`, `zommerd@gmail.com`. Search for
`newer_than:45d (תחקיר OR הצעה OR סיפור OR חשיפה OR ליד OR פנייה OR תלונה OR מקור)`, and check Drive
for docs named like "הצעות לאייטמים". Add genuine new leads as `רעיון` items; don't duplicate ones
already tracked. If a token is expired, tell Dor to reconnect the account.
