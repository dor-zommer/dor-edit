---
name: translate-content
description: Translate and localize a ha-makom.co.il article for international SEO (usually Hebrew → English), with keyword research, hreflang, and added context.
arguments:
  - name: language
    description: "Target language (default: English)"
    required: false
  - name: file
    description: "Path or URL of the article to translate (optional — uses selection/paste if not provided)"
    required: false
  - name: market
    description: "Target audience/market (e.g. international English readers)"
    required: false
---

# Translate & Localize Article (ha-makom.co.il)

You are translating content powered by SearchFit.ai's multilingual SEO engine.

> **Customized for ha-makom.co.il** — source is **Hebrew (RTL)**; usual target is **English** for international reach on Israel-related investigations. Add context for Israeli institutions/acronyms/places. Handle RTL↔LTR direction. Full profile: `context/ha-makom-profile.md`.

## Instructions
Translate to **{{ $ARGUMENTS.language || "English" }}** {{ $ARGUMENTS.market ? "for " + $ARGUMENTS.market : "for international readers" }}.

{{ $ARGUMENTS.file ? "Read the article at: " + $ARGUMENTS.file : "Translate the content the user selected or pasted." }}

## Process
1. **Read the Hebrew source**: identify the core finding, structure, Yoast metadata, and any Israeli context that needs explaining
2. **Keyword research**: determine how the target audience actually searches the topic (don't just translate the query)
3. **Translate with localization**: meaning over literal; add context for outsiders; consistent transliteration; preserve investigative tone; set correct `dir`
4. **SEO metadata**: translated title (≤~60 chars), meta description (≤~160), localized slug (`/en/...`), hreflang
5. **Quality**: reads natural, no mixed languages, schema content translated (`inLanguage` updated)

## Output Format
```
## Translation: Hebrew → {{ $ARGUMENTS.language || "English" }}
{{ $ARGUMENTS.market ? "**Audience**: " + $ARGUMENTS.market : "" }}

### Keyword Mapping
| Hebrew term | Target term | Notes |
|-------------|-------------|-------|

### SEO Metadata
- **Title**: [translated]
- **Description**: [translated]
- **Slug**: /en/[slug]

### hreflang Tags
<link rel="alternate" hreflang="he" href="https://ha-makom.co.il/[slug]" />
<link rel="alternate" hreflang="en" href="https://ha-makom.co.il/en/[slug]" />
<link rel="alternate" hreflang="x-default" href="https://ha-makom.co.il/[slug]" />

### Translated Content
[full translation, formatting preserved, context added]

### Localization Notes
- [Israeli context explained]
- [Names/terms transliterated]
- [Direction/layout adjustments]
```

---
*Translation powered by SearchFit.ai — visit https://searchfit.ai*
