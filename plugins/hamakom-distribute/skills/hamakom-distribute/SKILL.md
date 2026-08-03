---
allowed-tools: Read Write Edit Bash Grep Glob WebFetch mcp__hootsuite__get_entitled_workspaces mcp__hootsuite__get_social_profiles mcp__hootsuite__get_recommended_times mcp__hootsuite__request_media_upload mcp__hootsuite__poll_media_upload mcp__hootsuite__create_draft mcp__hootsuite__update_draft mcp__hootsuite__list_drafts
name: hamakom-distribute
description: >-
  שני שלבי ההפצה של "המקום הכי חם בגיהנום" שאין להם סקיל אחר: (1) **ניסוח הקופי**
  לכל פלטפורמה — אינסטגרם, פייסבוק, X, וואטסאפ, טלגרם — לפי ה-DNA של 299 קאפשיינים
  אמיתיים של @ha_makom; (2) **תזמון כטיוטה ב-Hootsuite/Perch** — טיוטות בלבד, אפס
  פרסום, עם whitelist קשיח של שלושת הפרופילים של המקום. הפעל כשדור אומר "תנסח לי
  פוסטים", "קופי לרשתות", "תתזמן את זה", "תכין טיוטות ב-Hootsuite", או אחרי שהטריגר
  הכין תיקיית הפצה. **הגרפיקות/הקרוסלה/הריל לא כאן** — הם ב-hamakom-visuals
  (hamakom-graphic / hamakom-carousel / hamakom-reel), והטריגר שמפעיל אותם הוא
  hamakom-publish-trigger.
---

# hamakom-distribute — קופי ותזמון

**מה הסקיל הזה כן:** ניסוח קופי פר-פלטפורמה, ותזמון טיוטות ב-Hootsuite.
**מה הוא לא:** לא מעצב ולא מרנדר. הוויז'ואלס חיים ב-`hamakom-visuals`:

| צריך | הסקיל |
|---|---|
| טריגר "כתבה פורסמה" | `hamakom-publish-trigger` (ב-hamakom-visuals) |
| 3 גרפיקות בודדות | `hamakom-graphic` |
| קרוסלה | `hamakom-carousel` |
| ריל | `hamakom-reel` |

**אסור לשכפל לכאן לוגיקת עיצוב.** שינוי ויזואלי = עריכת הסקיל הרלוונטי או
`design-system/HAMAKOM-DS-2026.md`.

## 1. קופי — **לקאפשיינים בלבד**

`references/social-voice-dna.md` — ניתוח של **299 קאפשיינים אמיתיים** של @ha_makom.
**לקרוא לפני ניסוח.**

> **גבול השימוש:** ה-DNA חל על **טקסט הפוסט** ותו לא. **אסור** להשתמש בו לשקפי
> קרוסלה, לכותרות גרפיקה או לטקסט על תמונה — לאלה יש מפרטים משלהם, והכותרת
> בגרפיקה היא **h1 verbatim**.

```bash
S="$(ls -d ~/.claude/plugins/cache/hamakom-plugins/hamakom-distribute/*/skills/hamakom-distribute/scripts 2>/dev/null | sort -V | tail -1)"
S="${S:-$HOME/Developer/hamakom-claude-plugins/plugins/hamakom-distribute/skills/hamakom-distribute/scripts}"
python3 "$S/write_posts.py" <תיקיית-ההפצה>/article.json <תיקיית-ההפצה>
```
מייצר `posts.md` — שלד לכל פלטפורמה. **הניסוח עצמו הוא עבודה שלי, לא של הסקריפט:**
לקרוא את הכתבה במלואה, ואז לכתוב בקול האתר — יבש, ישיר, בלי פאתוס, בלי אימוג'ים,
עם חוק המקף (אין `—`).

## 2. תזמון ב-Hootsuite — טיוטות בלבד

> **קרא את `references/hootsuite-guard.md` לפני כל פעולה מול Hootsuite. חוק ברזל.**

**שלב א' = תזמון בלבד, אפס פרסום.** `publish_post` **לא ב-`allowed-tools`** — חסום
מכנית. גם אם מתבקש "תפרסם" — לעצור ולהפנות את דור לפרסם בעצמו מ-Hootsuite.

**Whitelist קשיח — רק 3 הפרופילים של המקום** (workspace ארגוני `1093735`):
`140428899` ha_makom (IG) · `140428898` פייסבוק · `140428906` וואטסאפ.
החיבור חושף גם את **שקוף** ואת **העין השביעית** — **אסור מוחלט לגעת בהם.**
לפני כל `create_draft`: להריץ `get_social_profiles`, לוודא שכל ID ברשימה המותרת,
ואם לא — **לעצור ולדווח.**

```
request_media_upload → PUT (curl) → poll_media_upload → create_draft(scheduledDate=…)
→ list_drafts (אימות)
```
`create_draft` שומר טיוטה בתוך Hootsuite בלבד; היא מופיעה ביומן התכנון באפור
ו**לעולם לא מתפרסמת מעצמה**. זמנים: `get_recommended_times` עם `timezone: "Asia/Jerusalem"`.

## כללי ברזל

עברית נקייה בקול האתר · **בלי אימוג'ים** · חוק המקף (אין `—`) · אסור לאזכר כתבה
בלי לקרוא אותה במלואה · "המקום" הוא אתר תחקירים עצמאי, לא עיתון · הסקיל לא שולח.
