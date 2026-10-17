# בלוקים לוורדפרס - מה קיים באתר עכשיו

קובץ עזר לשלב 8 ולהזנה לאתר. אומת מול האתר ב-17 באוקטובר 2026.

## חוק: רק בלוקים שרשומים באתר

בלוק שאינו רשום באתר נשמר בטיוטה בלי שגיאה, אבל לא נרנדר: הקורא רואה חור, והעורך רואה ״הבלוק אינו נתמך״. לכן הרשימה בקובץ הזה היא נקודת פתיחה, והבדיקה החיה גוברת עליה. לפני הזנה, ובכל ספק:

```bash
# הפרטים מ-~/.claude/.env נשלפים ב-grep/cut ולא מודפסים
E=~/.claude/.env; g(){ grep -E "^$1=" "$E" | head -1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//'; }
B="$(g WP_BASE_URL)"; B="${B%/}"; B="${B%/wp-json}"
curl -sS -u "$(g WP_APP_USERNAME):$(g WP_APP_PASSWORD)" \
  "$B/wp-json/wp/v2/block-types?namespace=hmk&_fields=name,attributes"
```

ואחרי ההזנה: מושכים את הפוסט ב-`context=edit` ובודקים שכל בלוק שהוזן מופיע ב-`content.rendered`. בלוק שלא נרנדר הוא תקלה, לא ״יסתדר בעורך״.

### בלוקי hmk שרשומים (17 באוקטובר 2026)

| בלוק | שדות | שימוש |
|---|---|---|
| `hmk/brief` | `heading`, `items`, `collapsible`, `collapsed` | התקציר: ״הכתבה ב-99 מילים״, ״הטור ב-90 מילים״, ״בקצרה״ |
| `hmk/pullquote` | `quote`, `cite` | ציטוט מוגדל |
| `hmk/stat` | `n`, `t`, `sub`, `src` | נתון-מחץ |
| `hmk/findings` | `heading`, `items`, `collapsible`, `collapsed` | רשימת ממצאים |
| `hmk/bars` | `title`, `rows`, `src` | גרף עמודות |
| `hmk/related` | `heading`, `mode`, `count`, `urls` | תיבת ״קראו עוד״ - נטענת בתבנית, לא מזינים ידנית |
| `hmk/image-slider` | `images`, `title`, `ratio`, `perView`, `arrows`, `dots`, `captions`, `autoplay` | גלריית תמונות |
| `hmk/evcard` | `kind`, `heading`, `align`, `rows` | כרטיס מידע |
| `hmk/live`, `hmk/live-item` | `heading`, `newestFirst` / `date`, `time`, `title`, `hot` | עדכון חי |

### בוטלו - לא להשתמש

| ישן | במקומו |
|---|---|
| `hmk/sum99` | `hmk/brief` |
| `hmk/embed` | ההטמעה הרגילה של וורדפרס (`wp:embed`) עם מאפייני הכרטיס של המקום - ראו למטה |
| `hmk/stat` עם `label` | `hmk/stat` עם `t` |

## המרקאפ המדויק

**תקציר.** כל שורה ב-`items` הופכת לנקודה, ולכן תקציר רץ נכתב בשורה אחת, בלי `\n`. הכותרת: ״הכתבה ב-99 מילים״ בתחקיר ובכתבה, ״הטור ב-90 מילים״ בטור, ״בקצרה״ כשהתקציר הוא נקודות.

```html
<!-- wp:hmk/brief {"heading":"הכתבה ב-99 מילים","items":"<התקציר בשורה אחת>"} /-->
```

**ציטוט מוגדל.** המשפט מילה במילה, והוא נשאר גם בגוף.

```html
<!-- wp:hmk/pullquote {"quote":"<המשפט מילה במילה>","cite":"<ייחוס>"} /-->
```

ציטוט שהוא תשובה לשאלה מובא כחילופי הדברים, עם שם הדובר בכל שורה (ראו `dor-compass.md`). הבלוק מקבל `<strong>` ו-`<br>` בתוך `quote`; וורדפרס שומר אותם בקוד הבלוק כ-`<` ו-`>`. אומת שהוא נרנדר עם הדגשה ושבירת שורה:

```html
<!-- wp:hmk/pullquote {"quote":"<strong>מראיין:</strong> ״<השאלה>״<br><strong>גיל:</strong> ״<התשובה>״.","cite":"מתוך הראיון של אבי גיל בחדשות 12"} /-->
```

**נתון-מחץ.** השדה הוא `t`, לא `label`.

```html
<!-- wp:hmk/stat {"n":"10.8 מיליארד שקל","t":"<מה המספר אומר>"} /-->
```

**הטמעה של כתבה קודמת של המקום.** זו ההטמעה הרגילה של וורדפרס, עם ארבעה מאפיינים של תבנית המקום שהופכים אותה לכרטיס כהה גדול עם תקציר ותאריך. כך מוטמעות כתבות בכל הכתבות שפורסמו מאז ספטמבר 2026:

```html
<!-- wp:embed {"url":"https://www.ha-makom.co.il/<slug>/","type":"rich","providerNameSlug":"","hmkSize":"lg","hmkBg":"ink","hmkDek":true,"hmkDate":true} -->
<figure class="wp-block-embed is-type-rich"><div class="wp-block-embed__wrapper">
https://www.ha-makom.co.il/<slug>/
</div></figure>
<!-- /wp:embed -->
```

**סרטון מיוטיוב.**

```html
<!-- wp:embed {"url":"https://www.youtube.com/watch?v=<id>","type":"video","providerNameSlug":"youtube","responsive":true,"className":"wp-embed-aspect-16-9 wp-has-aspect-ratio"} -->
<figure class="wp-block-embed is-type-video is-provider-youtube wp-block-embed-youtube wp-embed-aspect-16-9 wp-has-aspect-ratio"><div class="wp-block-embed__wrapper">
https://www.youtube.com/watch?v=<id>
</div><figcaption class="wp-element-caption"><כיתוב> (<ערוץ>)</figcaption></figure>
<!-- /wp:embed -->
```

**נגן של אתר אחר** (מאקו, למשל), כשאין לו הטמעה רגילה: `wp:html` עם iframe ביחס 16:9. לפני ההזנה פותחים את כתובת הנגן בדפדפן ומוודאים שהיא מנגנת.

```html
<!-- wp:html -->
<figure class="wp-block-embed"><div style="position:relative;width:100%;padding-top:56.25%"><iframe src="<כתובת הנגן>" title="<תיאור>" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0" allowfullscreen loading="lazy"></iframe></div><figcaption class="wp-element-caption"><כיתוב></figcaption></figure>
<!-- /wp:html -->
```

**תמונה.** מעלים קודם לספריית המדיה (`POST /wp/v2/media`), ממלאים כותרת, טקסט חלופי וכיתוב, ואז:

```html
<!-- wp:image {"id":<media id>,"sizeSlug":"full","linkDestination":"none"} -->
<figure class="wp-block-image size-full"><img src="<url>" alt="<טקסט חלופי>" class="wp-image-<media id>"/><figcaption class="wp-element-caption"><כיתוב> (צילום: <צלם>/פלאש 90)</figcaption></figure>
<!-- /wp:image -->
```

**קובץ וידאו** שהועלה לספריית המדיה, עם תמונת פתיחה:

```html
<!-- wp:video {"id":<media id>} -->
<figure class="wp-block-video"><video controls poster="<url של תמונת הפתיחה>" preload="metadata" src="<url של הווידאו>"></video><figcaption class="wp-element-caption"><כיתוב> (וידאו: <מקור>)</figcaption></figure>
<!-- /wp:video -->
```

## חומר חזותי בגוף - חובה, לא לפי בקשה (דור, 17 באוקטובר 2026)

הזנה לאתר שאין בה את אלה איננה גמורה:

1. **המקור עצמו מוטמע.** הראיון, הדיווח או הסרטון שהכתבה נשענת עליו: הנגן המקורי, היוטיוב של הערוץ, או קובץ הווידאו המקורי שהועלה לספריית המדיה. ממוקם ליד הפסקה שמציגה אותו.
2. **צילומי מסך מהמקור עם כתוביות.** הפריים נלקח ברגע שבו נאמר המשפט שמופיע בגוף, וכל צילום ממוקם ליד הפסקה שלו. קרדיט: ״צילום מסך: <ערוץ>״. כתובית שלא הייתה בשידור והוספה במערכת מסומנת בכיתוב (״הכתובית הוספה במערכת״), ותמיד עם שם הדובר. לוגו של הערוץ המקורי נשאר; סימן מים של מי שהעלה עותק לרשת נחתך.
3. **צילומים של המעורבים.** פלאש 90, לע״מ, או קבצים שדור הוריד לתיקיית ההורדות. הקרדיט נלקח מנתוני הקובץ עצמו (IPTC: צלם, תאריך, כיתוב), לא מהזיכרון.
4. **תמונה ראשית** (חובה מאז 14.10.2026).

### מאיפה מביאים פריימים (לקחי 17 באוקטובר 2026)

- **ערוץ 14:** הווידאו בכתבה באתר הערוץ יושב על `https://channel14.vod.immergo.tv/channel14/transcoded/<guid>/hls/master.m3u8`. ה-guid מופיע בקוד הכתבה (`data-guid=`). `ffmpeg -ss <שניות> -i <...>/hls/6000k/streamPlaylist.m3u8 -frames:v 1` מוציא פריים ב-1080 בלי להוריד את כל הקובץ.
- **כאן 11 ו-ynet:** קובץ mp4 ישיר בקוד העמוד (ב-ynet: `progressive-video-ynet.ynethd.com/...mp4`), או הסרטון ביוטיוב של הערוץ.
- **יוטיוב:** `yt-dlp` במק. אם ה-mp4 מחזיר 403, לנסות `--extractor-args "youtube:player_client=web_embedded"`. אם גם זה נחסם - לנגן בדפדפן ולצייר את הפריים על canvas.
- **חדשות 12 (מאקו):** הנגן לא מאפשר הורדה, אבל ההטמעה עובדת: `https://www.mako.co.il/AjaxPage?jspName=embedHTML5video.jsp&galleryChannelId=<videoGalleryChannelId>&videoChannelId=<videoChannelId>&vcmid=<videoVcmId>`. שלושת המזהים מופיעים בקוד הכתבה. לפריימים: הסרטון של כאן או של ערוץ אחר שציטט את הראיון, עם קרדיט כפול (״צילום מסך: כאן 11, באדיבות חדשות 12״).
- **מציאת הרגע:** כתוביות אוטומטיות של יוטיוב בעברית (`yt-dlp --write-auto-subs --sub-langs iw`) נותנות שעה לכל משפט.
