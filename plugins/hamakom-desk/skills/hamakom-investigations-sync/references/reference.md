# Investigations DB — schema, mappings, and gotchas

## Property keys (use exactly — note the slashes)

| Field | Type | Notes |
|---|---|---|
| `Name` | title | article headline |
| `Status` | status | see options below |
| `סוג` | select | תחקיר / כתבה קצרה / טור / ניוזלטר / מגזין |
| `כתב/ת` | select | one of the six staff writers below (omit for external columnists) |
| `עורך/ת` | person | JSON string of a single user id, e.g. `["user://4fb1812b-9d58-4767-b010-651ca6c704df"]` |
| `פלטפורמה/מדיה` | select | המקום הכי חם / רשתות / ניוזלטר |
| `תאריך פרסום` | date | expanded form — see below |
| `תקציר` | text | put the dek + the `ha-makom.co.il/<slug>/` URL here (URL is the dedupe key) |
| `מקום` | place | optional geo |
| `Google Drive File` | relation | can't set by value — link Drive docs in the page body instead |
| `Tasks` | relation | to Tasks data source |

### Date property — expanded form
- `date:תאריך פרסום:start` = `"YYYY-MM-DD"`
- `date:תאריך פרסום:end` = omit for a single date
- `date:תאריך פרסום:is_datetime` = `0`

### Status options (pipeline order)
`רעיון` (To-do) → `איסוף` (To-do) → `תחקיר` → `כתיבה` → `עריכה` → `מוכן לפרסום` → `פורסם` → `ארכיון`

### סוג ← WordPress category mapping
- category contains `דעות` → `טור`
- category contains `מגזין` or `מראה מקום` → `מגזין`
- category contains `תחקיר` → `תחקיר`
- otherwise → `כתבה קצרה`

## Staff writers — WordPress author id → `כתב/ת`

Only these six exist in the `כתב/ת` select. For any other author id (external columnist / guest),
leave `כתב/ת` empty.

| author id | name |
|---|---|
| 5080 | דור זומר |
| 5234 | סיון תהל |
| 5217 | אילי פארי |
| 5084 | רויטל חובל |
| 4973 | שקד אורבך |
| 5276 | יהודה רחנייב |

Known external/guest author ids seen (do **not** map to `כתב/ת`): 5296 יותם יעקבסון, 5242 נדב תמיר,
5295 חנן אופנר, 5294 עילי אבידר, 5293 מתן פלום, 5292 אורי נרוב, 5287 אורן יפתחאל, 5224 מיקי לוזון,
2 מערכת המקום. (The WP `/users` endpoint is locked, so infer new author ids from a known article by
that author, or ask Dor.)

## WordPress REST gotchas

- `web_fetch` strips `_fields` and similar params and returns an empty body for large lists.
  Use the browser (`fetch()` in `javascript_tool`) for anything that needs `_fields`.
- `context=embed` drops the huge `content` field but still carries a large `yoast_head` block —
  not compact enough; prefer explicit `_fields`.
- The browser tool truncates large return values. Store results on `window.__X` and read back in
  slices of ~5–10 rows.
- Hebrew text in URL query strings (e.g. `?search=...`) can hit a privacy/cookie block — avoid
  putting Hebrew in query params; filter client-side instead.
- Useful fields: `date`, `slug`, `title.rendered`, `author`, `categories`, `excerpt.rendered`,
  `jetpack_featured_media_url` (hero image).
- Decode HTML entities from titles/excerpts: `&quot;`→`"`, `&#8211;`→`–`, `&#8217;`→`’`,
  `&#8220;`→`“`, `&#8221;`→`”`, `&#8230;`→`…`, `&nbsp;`→space.

## Categories map (id lookup)
Fetch once per run: `/wp-json/wp/v2/categories?per_page=100&_fields=id,name,parent`, then map each
post's `categories` ids to names before applying the סוג rule above.
