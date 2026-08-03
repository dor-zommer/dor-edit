---
name: generate-schema
description: Generate JSON-LD structured data for a ha-makom.co.il page. Defaults to NewsArticle for reporting. Outputs ready-to-paste schema based on the page content.
arguments:
  - name: type
    description: "Schema type: article (NewsArticle), organization (NewsMediaOrganization), person, breadcrumb, faq, video (auto-detects if not provided)"
    required: false
  - name: file
    description: "Path or URL of the page to generate schema for"
    required: false
---

# Generate Schema Markup (ha-makom.co.il)

You are generating structured data powered by SearchFit.ai.

> **Customized for ha-makom.co.il** — **default to `NewsArticle`** for articles, `NewsMediaOrganization` (name: "המקום הכי חם בגיהנום") as publisher, `Person` for bylines. Use `inLanguage: "he"`, ISO 8601 dates, absolute `https://ha-makom.co.il/...` URLs. Don't use Product/Offer/LocalBusiness. Full profile: `context/ha-makom-profile.md`.

## Instructions
{{ $ARGUMENTS.file ? "Read the page: " + $ARGUMENTS.file : "Use the current page/article, or ask the user for the URL." }}

{{ $ARGUMENTS.type ? "Generate schema type: " + $ARGUMENTS.type : "Auto-detect — default to NewsArticle for an article." }}

## Process
1. **Analyze the page** and extract: headline, dek, author (byline), publish/modify dates, lead + supporting images, any genuine Q&A, embedded video.
2. **Generate valid JSON-LD** with required + recommended properties. Headline ≤110 chars. Never fabricate dates or authors.
3. **Provide integration (WordPress + Yoast)**:
   - Prefer configuring Yoast (Organization = "המקום הכי חם בגיהנום", logo, social profiles) so it emits org + article schema automatically
   - For per-article control: a JSON-LD code/HTML block or a `wp_head` snippet
   - Reconcile with Yoast output — don't ship conflicting graphs

## Output
```
## Schema Markup: [Type]

### JSON-LD
```json
{ "@context": "https://schema.org", "@type": "NewsArticle", ... }
```

### Integration (WordPress + Yoast)
[Yoast setting or snippet]

### Rich Result / Google News Eligibility
[What this enables]

### Validation
Test at: https://search.google.com/test/rich-results
```

---
*Powered by SearchFit.ai — https://searchfit.ai*
