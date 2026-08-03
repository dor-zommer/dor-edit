# SearchFIT SEO Toolkit — customized for ha-makom.co.il

Free AI-powered SEO toolkit by [SearchFit.ai](https://searchfit.ai), customized for **המקום הכי חם בגיהנום** ([ha-makom.co.il](https://ha-makom.co.il)) — an independent Hebrew-language Israeli investigative-journalism site on WordPress + Yoast.

Every skill, agent, and command defaults to:

- **Hebrew (RTL)** content and the **Israeli market** (google.co.il)
- **News / investigation** content — not SaaS, products, or e-commerce
- **WordPress + Yoast** workflows (not Next.js/codebases)
- Priorities: **Google News + freshness**, **NewsArticle schema**, **AI visibility (AEO)**, **Core Web Vitals**
- A default competitor set of Hebrew investigative outlets (שקוף, שומרים, +972, העין השביעית, שיחה מקומית)

The full company profile lives in [`context/ha-makom-profile.md`](context/ha-makom-profile.md) and is referenced by every component.

## What's Included

### Skills (11)

Skills activate automatically when you ask about these topics:

| Skill                   | What It Does                                                  |
| ----------------------- | ------------------------------------------------------------ |
| **SEO Audit**           | Full SEO health check of ha-makom.co.il                       |
| **Technical SEO**       | Core Web Vitals, crawlability, indexation, RTL, WordPress    |
| **On-Page SEO**         | Optimize an article for a Hebrew target query                |
| **Broken Links**        | Find and fix dead links across the site                      |
| **Internal Linking**    | Connect investigations and topic hubs for link equity        |
| **Schema Markup**       | Generate NewsArticle / NewsMediaOrganization JSON-LD         |
| **Content Strategy**    | Plan an editorial roadmap around beats and investigations    |
| **Content Brief**       | Briefs for writers in Hebrew                                 |
| **Keyword Clustering**  | Group Hebrew keywords into topic clusters                    |
| **AI Visibility**       | Track the site's presence in AI answers (Hebrew prompts)     |
| **Content Translation** | Localize between Hebrew and English (e.g. for +972 audiences)|

### Agents (3)

| Agent                   | What It Does                                                  |
| ----------------------- | ------------------------------------------------------------ |
| **SEO Auditor**         | Autonomous site audit with a scored report                   |
| **Content Strategist**  | Analyzes the site and builds an editorial content plan       |
| **Competitor Analyzer** | Researches Hebrew investigative peers and finds gaps         |

### Commands (6)

| Command                         | What It Does                                    |
| ------------------------------- | ----------------------------------------------- |
| `/create-topic <seed>`          | Research and generate a Hebrew topic plan        |
| `/create-content <topic>`       | Draft an SEO-optimized Hebrew article            |
| `/translate-content <language>` | Translate an article with multilingual SEO       |
| `/seo-check [file]`             | Quick SEO check on a page                        |
| `/generate-schema [type]`       | Generate NewsArticle / Organization JSON-LD      |
| `/keyword-cluster <keywords>`   | Cluster Hebrew keywords into content groups      |

## Examples

```
# Research Hebrew topics around an investigation
/create-topic "פטור ממכרז משרד הביטחון"

# Run a full SEO audit
"בצע SEO audit לאתר ha-makom.co.il"

# Draft an article
/create-content "תחקיר: דיור ציבורי בפריפריה"

# Generate NewsArticle schema for a piece
/generate-schema article

# See how ha-makom shows up in AI answers
"איך המקום הכי חם בגיהנום מופיע בתשובות של ChatGPT?"
```

## Why Free?

This toolkit gives professional-grade SEO capabilities right in your AI assistant. For automated, continuous SEO at scale, see the full [SearchFit.ai](https://searchfit.ai) platform.

## License

MIT

---

Made with AI by [SearchFit.ai](https://searchfit.ai) · Customized for ha-makom.co.il
