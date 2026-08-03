=== המקום — עמוד נתונים (סקאפולד תוסף) ===
גרסה: 1.0.0

מה זה
-----
שלד תוסף שמטמיע עמוד נתונים אינטראקטיבי (scrollytelling) בתוך iframe מבודד.
שורטקוד יחיד שמופק מ-PLUGIN.php.

שכפול לעמוד חדש
---------------
1. שנה שם תיקייה+קובץ: hamakom-<slug>/hamakom-<slug>.php
2. ב-PLUGIN.php החלף:  SHORTCODE → hamakom_<slug>  ,  hmk_data_ → hmk_<slug>_
   ועדכן Plugin Name / Description / title של ה-iframe.
3. שים את העמוד והנתונים תחת app/ (ראה מבנה למטה).

מבנה
-----
hamakom-<slug>.php        — השורטקוד (פולט iframe בלבד)
app/index.html            — העמוד המלא, עצמאי (מהטמפלייט של הסקיל)
app/*.geojson, *.json     — נתוני המפה/הסיקור (נטענים יחסית מתוך app/)
app/layers/               — שכבות מפה (אם יש)
app/vendor/leaflet/       — עותק מקומי של Leaflet (ללא CDN; לשכתב את ה-refs ב-index.html)

אריזה
-----
cd wp-plugin && zip -rq ../hamakom-<slug>.zip hamakom-<slug>
  - בעדכון עמוד חי: שמור את שם ה-ZIP זהה לקיים (אחרת WP מבקש התקנה כפולה).
  - ודא שאין .DS_Store ב-ZIP.

התקנה
-----
תוספים > הוסף תוסף > העלאת תוסף > בחר ZIP > התקן > הפעל.
צור/ערוך עמוד והדבק בגוף התוכן (Text Block / Raw HTML ב-WPBakery):  [hamakom_<slug>]

למה iframe
----------
בידוד CSS/JS מוחלט מול JNews/WPBakery/WP-Rocket — אפס מלחמות !important, אפס
התנגשות עם בלוקים אחרים. שטח תקיפה = קובץ סטטי בלבד.

תלויות חיצוניות תקינות שנותרות: אריחי מפה מ-CartoDB, גופנים מ-Google Fonts.
