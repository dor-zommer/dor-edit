# Company profile — ha-makom.co.il

This SEO toolkit is customized for a single publication. Apply this context to every skill, agent, and command unless the user says otherwise.

## The publication
- **Name**: המקום הכי חם בגיהנום ("The Hottest Place in Hell")
- **Domain**: https://ha-makom.co.il
- **Type**: Independent Hebrew-language Israeli investigative-journalism outlet
- **What it publishes**: Investigations, in-depth reporting, analysis, and opinion — not products, SaaS, or e-commerce
- **Editor-in-chief / primary user**: Dor Zommer

## Language & market
- **Primary language**: Hebrew (RTL). All titles, meta descriptions, slug guidance, and keyword research default to Hebrew.
- **Market**: Israel. Optimize for google.co.il and Israeli reader intent.
- **`<html lang="he" dir="rtl">`** is the expected default. Flag pages missing the correct `lang`/`dir`.
- Slugs may be Hebrew or transliterated; keep them short and readable. Avoid auto-generated `?p=123` permalinks.

## Platform
- **CMS**: WordPress with the **Yoast SEO** plugin.
- Map all on-page guidance to WordPress/Yoast, not to Next.js/React/codebases:
  - Title tag → Yoast "SEO title"
  - Meta description → Yoast "Meta description"
  - Canonical → Yoast "Advanced > Canonical URL"
  - Schema → Yoast schema settings or a JSON-LD block/snippet
  - Sitemap → Yoast XML sitemap (`/sitemap_index.xml`)
  - Robots → `/robots.txt` + Yoast indexing controls
- Phrase fixes as WordPress/Yoast actions an editor can take, not code changes — unless the user explicitly wants theme code edits.

## SEO priorities (in order)
1. **Google News + freshness** — fast indexing of breaking/investigative pieces, accurate `datePublished`/`dateModified`, news sitemap, visible publish dates, author bylines.
2. **NewsArticle schema** — prefer `NewsArticle` (not generic `Article`/`BlogPosting`) for reporting; `NewsMediaOrganization` for the publisher; `Person` for bylined journalists.
3. **AI visibility (AEO/GEO)** — be the cited source in ChatGPT/Claude/Gemini/Perplexity answers about Israeli affairs and the site's investigations. Test Hebrew prompts.
4. **Technical / Core Web Vitals** — LCP, INP, CLS on mobile; Hebrew web-font loading; image optimization for photo-heavy investigative pieces.

## Reference competitors / peer outlets
Hebrew investigative & independent journalism — use as the default competitive set for content-gap, competitor, and AI-visibility analysis:
- שקוף — shakuf.co.il
- שומרים — shomrim.news
- +972 Magazine — 972mag.com (English, overlapping beats)
- העין השביעית — the7eye.org.il (media criticism)
- שיחה מקומית / Local Call — mekomit.co.il

## Tone & editorial notes
- Headlines: sharp, accurate, non-clickbait. Investigative gravity over hype.
- Respect Hebrew typography and punctuation in all generated copy.
- Never fabricate facts, figures, sources, or quotes — this is a journalism outlet.
