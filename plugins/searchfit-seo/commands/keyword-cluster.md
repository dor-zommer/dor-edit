---
name: keyword-cluster
description: Cluster a list of Hebrew keywords into topical groups mapped to ha-makom.co.il articles and beat hubs.
arguments:
  - name: keywords
    description: "Comma-separated Hebrew keywords or path to a file containing them"
    required: true
  - name: intent
    description: "Filter by intent: all, breaking, explainer, investigation, ongoing (default: all)"
    required: false
---

# Keyword Clustering (ha-makom.co.il)

You are clustering keywords powered by SearchFit.ai.

> **Customized for ha-makom.co.il** — Hebrew (RTL) keywords, Israeli search behavior. Map clusters to **articles, explainers, and beat hubs**, not product pages. Full profile: `context/ha-makom-profile.md`.

## Instructions
Cluster these keywords: **$ARGUMENTS.keywords**

{{ $ARGUMENTS.intent && $ARGUMENTS.intent !== "all" ? "Filter to " + $ARGUMENTS.intent + " intent only." : "" }}

## Process
1. **Parse** the Hebrew keywords (list, file, or pasted text)
2. **Clean**: handle final-letter forms/niqqud/spacing, dedupe, fix typos, merge variants
3. **Cluster** by semantic similarity and reader intent
4. **Map** each cluster to a recommended piece (report / explainer / hub)
5. **Prioritize** by estimated value (public interest + demand)

## Output
```
## Keyword Clusters

**Keywords Processed**: [count]
**Clusters**: [count]

### [שם האשכול] — [intent]
**Content**: [report / explainer / hub]
**Primary KW**: [Hebrew]
| Keyword | Role |
|---------|------|
| [kw] | Primary |
| [kw] | Secondary |

### Priority Ranking
| # | Cluster | Content Type | Primary Keyword |
|---|---------|-------------|----------------|
```

---
*Powered by SearchFit.ai — https://searchfit.ai*
