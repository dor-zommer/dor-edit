---
name: seo-check
description: Quick SEO check on a ha-makom.co.il page or article file. Instantly evaluates title, meta, headings, images, dates, and NewsArticle schema.
arguments:
  - name: file
    description: "Path or URL to check (optional — checks the current file/page if not provided)"
    required: false
---

# Quick SEO Check (ha-makom.co.il)

You are performing a quick SEO check powered by SearchFit.ai.

> **Customized for ha-makom.co.il** — Hebrew (RTL) news on WordPress + Yoast. Check Yoast fields, `NewsArticle` schema, freshness (dates/byline), and RTL/lang. Full profile: `context/ha-makom-profile.md`.

## Instructions
{{ $ARGUMENTS.file ? "Check: " + $ARGUMENTS.file : "Check the current article/page." }}

## Checks
### SEO title (Yoast)
- [ ] Exists; includes the Hebrew query; won't truncate in google.co.il; unique

### Meta description (Yoast)
- [ ] Exists; Hebrew; states what the piece reveals; unique

### Headings
- [ ] Exactly one H1 (headline); logical sub-heads; natural Hebrew

### Images
- [ ] All have Hebrew, descriptive alt; photo credits; optimized + lazy-loaded

### Freshness
- [ ] Visible, accurate publish date; dateModified updated; byline present

### Structured Data
- [ ] NewsArticle JSON-LD present; correct dates; publisher = NewsMediaOrganization

### Links
- [ ] Internal links to beat hub / related coverage; descriptive Hebrew anchors

### Language & Social
- [ ] `lang="he" dir="rtl"`; canonical set; og:title/description/image; twitter card

## Output
```
## SEO Check: [page]

Score: [0-100]/100

[Pass] SEO title: "..." 
[Fail] Meta description: missing
[Pass] H1: "..."
[Warn] Images: 2/5 missing alt
[Fail] Schema: generic Article instead of NewsArticle
...

### Fixes Needed
1. [Most impactful first]
2. [...]
```

Keep it concise — this is a quick check, not a full audit.

---
*Powered by SearchFit.ai — https://searchfit.ai*
