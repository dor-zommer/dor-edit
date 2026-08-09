# מסלולי פולבק למסירה - dor-edit

נטען רק כשמסלול א (SUGGEST) נכשל. המסלול הראשי מתועד ב-SKILL.md.

## מתי עוברים לפולבק

- `--suggest` החזיר `overwrote: true` (אפס הצעות חדשות למרות בקשות פעילות) - SUGGEST נבלע לדריסה. עצור מיד, אל תמסור, התריע לדור, ועבור למסלול ב.
- שגיאת API עקבית שגם retry לא פותר.

רקע: SUGGEST הוא Developer Preview. על פרויקט לא רשום (או כשהאישור נשבר) הבקשה מחזירה 200 בלי שגיאה - והשינוי נכתב כעריכה ישירה, כלומר דריסה שקטה. לכן בדיקת `clean`/`overwrote` היא חובה אחרי כל ריצה, לעולם לא מניחים שעבד. הטוקן חייב להיות מהפרויקט הרשום ל-Preview (הסקריפט משתמש בטוקני gmail-multi; מיקום הריפו נשלט ב-`GMAIL_MULTI_DIR`).

## מסלול ב - הצעות דרך docx-import (עם תגית)

בונים docx עם track changes בשם "דור זומר" דרך hamakom-edit-core, מעלים וממירים ל-Google Doc. ההמרה מייצרת הצעות נייטיביות אמיתיות, אבל עם תגית `suggestIdImport` בלתי עקיפה (בלי ייחוס אישי ברמת המשתמש; העלאה מהטוקן של דור אינה מסירה אותה).

```bash
DE=$(ls -d ~/.claude/plugins/cache/dor-private-plugins/dor-edit/*/skills/dor-edit 2>/dev/null | sort -V | tail -1); DE=${DE:-~/.claude/skills/dor-edit}
EC=~/.claude/skills/hamakom-edit-core
python3 "$EC/scripts/office/unpack.py" baseline.docx <workdir>
# הזרקת השינויים כ-track changes: from track_change import replace_run (author "דור זומר", change-id ייחודי)
# הערות: python3 comment.py <workdir> <id> "<טקסט>" --author "דור זומר"
python3 "$EC/scripts/office/pack.py" <workdir> edited-tracked.docx
python3 "$DE/scripts/upload_to_gdocs.py" edited-tracked.docx --name "<כותרת> - עריכת דור"
```

אמת ב-`documents.get` שקיימים `suggestedInsertionIds`/`suggestedDeletionIds` לפני שממשיכים. במסלול הזה הערות Docs מעוגנות אמיתיות כן אפשריות (מהייבוא) - אבל מדיניות הבית היא שהערות עורך יושבות בדוח, לא בשוליים.

## מוצא אחרון - Compare Documents בדפדפן

הצעות אמיתיות מיוחסות לדור, אבל דורש כרום ושורף טוקנים. רק אם ה-API כולו לא זמין.
בנה גרסה ערוכה זמנית, ואז בכרום (mcp__claude-in-chrome): פתח את מסמך המקור, Tools, Compare documents, בחר את הזמני, Attribute differences to: דור זומר, Compare.
כללי דפדפן: בלי קיצורי Cmd (תפריטים בלבד); ודא בצילום מסך שהדיאלוג פתוח לפני הקלדה; בלי cmd+a (triple_click בלבד). מחק את הזמני בסוף (drive_trash).

## מה שנפסל - לא לחזור

- יישום עריכות אחת-אחת בדפדפן במצב Suggesting: 30+ דקות לכתבה, שביר. נפסל סופית.
- מסלול visual-diff (`--propose`/`--resolve`): נמחק מהקוד ב-0.9.0 - הכרעה גורפת בלבד, ובאג שמחק קו-חוצה של דור.
- הערות Drive API על Google Doc: לא נתמכות כהערות מעוגנות (מגבלה מתועדת של גוגל). ההערה נוצרת, מוחזר id, ודור לא רואה כלום. אימות אם השאלה תחזור: ייצוא docx וספירת `<w:commentRangeStart` - אפס = לא מעוגן.
