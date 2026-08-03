קטעי קוד מוכנים — כל קומפוננטה מגיעה עם CSS + HTML + JS להדבקה לתוך template/index.html (CSS לתוך ה-<style>, HTML לתוך ה-<body>, JS לתוך ה-<script>).

---

## Waffle (רשת 10×10 לאחוזים)

שתי רשתות 10×10 שמשוות שיעור אישור בין שני מגזרים; הצעדים מדליקים אחוז (lit), דחיות (lit2) ותקועות (stuck) ומונים אחוז גדול.

```css
/* ---------- waffle ---------- */
.waffles{display:flex; gap:clamp(20px,4vw,52px); width:100%; max-width:560px; justify-content:center}
.wf{flex:1; max-width:240px}
.wf__head{display:flex; justify-content:space-between; align-items:baseline; border-bottom:2px solid var(--ink); padding-bottom:8px; margin-bottom:14px}
.wf__name{font-family:"Suez One",serif; font-size:1.05rem}
.wf__pct{font-family:"Suez One",serif; font-size:clamp(2rem,5vw,3rem); line-height:1; transition:color .4s}
.wf__pct small{font-family:"IBM Plex Sans Hebrew"; font-size:.34em; font-weight:600; color:#6b6b66}
.wf__sub{font-size:.82rem; color:#6b6b66; margin:2px 0 14px}
.waffle{display:grid; grid-template-columns:repeat(10,1fr); grid-template-rows:repeat(10,1fr); gap:4px; aspect-ratio:1/1}
.cell{border-radius:2px; border:1.4px dashed var(--line); background:#fff; transition:background-color .5s, border-color .5s, transform .4s}
.waffle.lit .cell[data-t="app"]{background:var(--terra); border-color:var(--terra); border-style:solid}
.waffle.lit2 .cell[data-t="rej"]{background:#c4c0b4; border-color:#c4c0b4; border-style:solid}
.waffle.stuck .cell[data-t="pen"]{border-color:var(--heather); border-style:dashed; background:rgba(142,111,168,.1)}
```

```html
<!-- בתוך section.scrolly > .scrolly__inner, אחרי .scrolly__steps -->
<div class="scrolly__graphic">
  <div class="gtitle">תוכניות לפי מגזר ותוצאה</div>
  <div class="waffles">
    <div class="wf">
      <div class="wf__head"><span class="wf__name">פלסטיני</span><span class="wf__pct" data-pct="32.3"><span class="n">0</span><small>%</small></span></div>
      <div class="wf__sub">439 תוכניות</div>
      <div class="waffle" id="wfPal"></div>
    </div>
    <div class="wf">
      <div class="wf__head"><span class="wf__name">התנחלויות</span><span class="wf__pct" data-pct="70.3"><span class="n">0</span><small>%</small></span></div>
      <div class="wf__sub">1,836 תוכניות</div>
      <div class="waffle" id="wfJew"></div>
    </div>
  </div>
</div>
```

```js
/* ---- WAFFLE build ---- */
function buildWaffle(elId, app, rej){
  var w=document.getElementById(elId), pen=100-app-rej, order=[],i;
  for(i=0;i<app;i++)order.push('app'); for(i=0;i<rej;i++)order.push('rej'); for(i=0;i<pen;i++)order.push('pen');
  order.forEach(function(t){var c=document.createElement('div');c.className='cell';c.dataset.t=t;w.appendChild(c);});
}
buildWaffle('wfJew',70,8); buildWaffle('wfPal',32,6);
(function(){
  var jew=document.getElementById('wfJew'), pal=document.getElementById('wfPal');
  var pctJ=document.querySelector('#act-approval .wf:nth-child(2) .wf__pct'),
      pctP=document.querySelector('#act-approval .wf:nth-child(1) .wf__pct');
  function setPct(el,v){countTo(el.querySelector('.n'), v, 800, function(x){return x.toFixed(1);});}
  function pctOnce(el,v){if(el.dataset.done==='1')return; el.dataset.done='1'; setPct(el,v);}
  function pctReset(el){el.dataset.done=''; el.querySelector('.n').textContent='0';}
  scrolly('#wfSteps', function(i){
    jew.classList.toggle('lit', i>=1);
    pal.classList.toggle('lit', i>=2);
    var s3=i>=3;
    jew.classList.toggle('lit2',s3); jew.classList.toggle('stuck',s3);
    pal.classList.toggle('lit2',s3); pal.classList.toggle('stuck',s3);
    if(i>=1)pctOnce(pctJ,70.3); else pctReset(pctJ);
    if(i>=2)pctOnce(pctP,32.3); else pctReset(pctP);
  });
})();
```

---

## השוואת מספר-גדול (unit gap)

שני מספרים מוחלטים זה מול זה ("מול") עם שורת מסקנה — אין JS, הערכים סטטיים ב-HTML.

```css
/* ---------- unit gap ---------- */
.unitgap{margin:clamp(28px,5vw,52px) auto 0; max-width:680px; text-align:center}
.unitgap__lead{font-size:clamp(1rem,2.4vw,1.18rem); color:var(--ink); margin-bottom:22px}
.unitgap__row{display:flex; align-items:center; justify-content:center; gap:clamp(16px,4vw,40px); flex-wrap:wrap}
.unitgap__side{display:flex; flex-direction:column; gap:4px}
.unitgap__num{font-family:"Suez One",serif; font-size:clamp(2.6rem,8vw,4.6rem); line-height:.95; color:var(--terra)}
.unitgap__side--pal .unitgap__num{color:var(--heather)}
.unitgap__lbl{font-size:.92rem; color:#6b6b66; max-width:16ch}
.unitgap__vs{font-family:"Suez One",serif; font-size:1.1rem; color:#9a978d}
.unitgap__foot{margin-top:22px; font-size:clamp(1rem,2.4vw,1.2rem); font-weight:600; color:var(--terra-deep); max-width:40ch; margin-inline:auto; line-height:1.5}
```

```html
<div class="unitgap reveal">
  <p class="unitgap__lead">ואותו פער, במספרים מוחלטים — יחידות דיור מאושרות בתוכניות:</p>
  <div class="unitgap__row">
    <div class="unitgap__side">
      <span class="unitgap__num">128,233</span>
      <span class="unitgap__lbl">יח״ד בתוכניות התנחלות</span>
    </div>
    <span class="unitgap__vs">מול</span>
    <div class="unitgap__side unitgap__side--pal">
      <span class="unitgap__num">669</span>
      <span class="unitgap__lbl">יח״ד בתוכניות פלסטיניות</span>
    </div>
  </div>
  <p class="unitgap__foot">פער התוכניות הוא פי 4. פער יחידות הדיור — כמעט פי 200.</p>
</div>
```

הערה: הספרות ב-`.unitgap__num` מוצגות סטטיות. אם רוצים אנימציית ספירה, עטפו ב-`<span class="n">0</span>` והפעילו `countTo` כמו ב-waffle.

---

## בועות יחס (proportional bubbles)

שלוש בועות ב-SVG שגודלן ∝ √סכום; הצעדים חושפים אותן אחת-אחת ומעדכנים כיתוב.

```css
/* ---------- money bubbles ---------- */
.bubbles{width:100%; max-width:480px; margin:0 auto}
.bubbles svg{width:100%; height:auto; overflow:visible}
.bub{transition:r 1s cubic-bezier(.2,.85,.25,1)}
.bub--a{fill:var(--terra)} .bub--b{fill:var(--sage)} .bub--c{fill:var(--heather)}
.bubTxt{opacity:0; transition:opacity .55s; text-anchor:middle; fill:#fff; font-family:"IBM Plex Sans Hebrew",sans-serif}
.bubTxt.on{opacity:1}
.bubAmt{font-family:"Suez One",serif; font-size:30px}
.bubName{font-size:13px; font-weight:600}
.bubName--out{fill:var(--ink)}
.bubcap{text-align:center; margin-top:18px}
.bubcap__n{font-family:"Suez One",serif; font-size:clamp(1.6rem,4.5vw,2.4rem); color:var(--terra-deep); line-height:1}
.bubcap__s{font-size:.95rem; color:#6b6b66; margin-top:8px; max-width:36ch; margin-inline:auto; line-height:1.5; min-height:3em}
```

```html
<div class="scrolly__graphic">
  <div class="gtitle">כסף ציבורי בפטור ממכרז · כל עיגול לפי גודל הסכום</div>
  <div class="bubbles">
    <svg viewBox="0 0 470 400" role="img" aria-label="עיגולים פרופורציונליים לסכומי ההתקשרויות">
      <circle class="bub bub--a" id="bubA" cx="132" cy="165" r="0"/>
      <circle class="bub bub--b" id="bubB" cx="338" cy="165" r="0"/>
      <circle class="bub bub--c" id="bubC" cx="235" cy="312" r="0"/>
      <text class="bubTxt bubAmt" id="bubAmtA" x="132" y="160">₪437M</text>
      <text class="bubTxt bubName" id="bubNameA" x="132" y="182">החטיבה להתיישבות</text>
      <text class="bubTxt bubAmt" id="bubAmtB" x="338" y="160">₪440M</text>
      <text class="bubTxt bubName" id="bubNameB" x="338" y="182">מתפ״ש</text>
      <text class="bubTxt bubAmt" id="bubAmtC" x="235" y="312" style="font-size:20px">₪112M</text>
      <text class="bubTxt bubName bubName--out" id="bubNameC" x="235" y="372">עיריית מעלה אדומים</text>
    </svg>
  </div>
  <div class="bubcap">
    <div class="bubcap__n" id="payCap">מאחורי כל תוכנית — תקציב</div>
    <div class="bubcap__s" id="payCapSub">כסף ציבורי שזורם אל הגופים שבונים בגדה — לרוב בפטור ממכרז</div>
  </div>
</div>
```

```js
/* ---- FINANCING (who pays, scrolly proportional bubbles) ---- */
(function(){
  var bubA=document.getElementById('bubA'), bubB=document.getElementById('bubB'), bubC=document.getElementById('bubC');
  if(!bubA) return;
  var cap=document.getElementById('payCap'), sub=document.getElementById('payCapSub');
  var MAX=93; // radius for ~440M; r ∝ sqrt(amount)
  var rA=Math.round(MAX*Math.sqrt(437/440)), rB=MAX, rC=Math.round(MAX*Math.sqrt(112/440));
  function txt(id,on){ var e=document.getElementById(id); if(e) e.classList.toggle('on',on); }
  function setBubbles(a,b,c){
    bubA.setAttribute('r', a?rA:0); bubB.setAttribute('r', b?rB:0); bubC.setAttribute('r', c?rC:0);
    txt('bubAmtA',a); txt('bubNameA',a); txt('bubAmtB',b); txt('bubNameB',b); txt('bubAmtC',c); txt('bubNameC',c);
  }
  var S=[
    {a:0,b:0,c:0, n:'מאחורי כל תוכנית — תקציב', s:'כסף ציבורי שזורם אל הגופים שבונים בגדה — לרוב בפטור ממכרז'},
    {a:1,b:0,c:0, n:'₪437 מיליון', s:'לחטיבה להתיישבות — מרביתם ממשרד החקלאות, "בעבור העודפים המחויבים"'},
    {a:1,b:1,c:0, n:'₪440 מיליון נוספים', s:'מתפ״ש — 119 התקשרויות בפטור ממכרז, כולן ביהודה ושומרון'},
    {a:1,b:1,c:1, n:'כמעט מיליארד ₪', s:'החטיבה + מתפ״ש + עיריית מעלה אדומים — כסף, תכנון וחקיקה לאותו כיוון'}
  ];
  var cur=-1;
  function show(i){ if(i===cur)return; cur=i; var s=S[i]||S[0]; setBubbles(s.a,s.b,s.c); cap.textContent=s.n; sub.textContent=s.s; }
  show(0);
  scrolly('#paySteps', show);
})();
```

---

## ברי קצב (rate bars)

שני ברים אופקיים שמשווים ממוצע לשנה בין שתי תקופות; הצעדים חושפים ברים ומחליפים כיתוב.

```css
/* ---------- annexation: rate comparison bars ---------- */
.ratebars{width:100%; max-width:520px; margin:14px auto 0; display:flex; flex-direction:column; gap:34px}
.ratebar{opacity:0; transform:translateY(8px); transition:opacity .5s ease, transform .5s ease}
.ratebar.in{opacity:1; transform:none}
.ratebar__head{display:flex; justify-content:space-between; align-items:baseline; margin-bottom:9px; gap:12px}
.ratebar__yrs{font-family:"Suez One",serif; font-size:1.05rem; color:#6b6b66; font-variant-numeric:tabular-nums}
.ratebar__rate{font-variant-numeric:tabular-nums; color:var(--ink); white-space:nowrap}
.ratebar__rate b{font-family:"Suez One",serif; font-size:2rem; color:var(--terra)}
.ratebar__rate small{font-size:.92rem; color:#6b6b66}
.ratebar__track{width:100%; height:32px; background:var(--paper); border-radius:7px; overflow:hidden}
.ratebar__fill{display:block; height:100%; width:0; background:var(--terra); border-radius:7px; transition:width 1s cubic-bezier(.2,.8,.2,1)}
.ratebar.in .ratebar__fill{width:var(--w)}
.ratebar[data-rb="0"] .ratebar__rate b{color:var(--sage)}
.ratebar[data-rb="0"] .ratebar__fill{background:var(--sage)}
```

```html
<div class="scrolly__graphic">
  <div class="gtitle">קצב צווי השיפוט · ממוצע צווים לשנה</div>
  <div class="ratebars" id="rateBars">
    <div class="ratebar" data-rb="0">
      <div class="ratebar__head"><span class="ratebar__yrs">2001–2022</span><span class="ratebar__rate"><b>5</b><small> צווים / שנה</small></span></div>
      <div class="ratebar__track"><span class="ratebar__fill" style="--w:13%"></span></div>
    </div>
    <div class="ratebar" data-rb="1">
      <div class="ratebar__head"><span class="ratebar__yrs">2023–2026</span><span class="ratebar__rate"><b>38</b><small> צווים / שנה</small></span></div>
      <div class="ratebar__track"><span class="ratebar__fill" style="--w:100%"></span></div>
    </div>
  </div>
  <div class="bubcap">
    <div class="bubcap__n" id="annexCap">"שטח שיפוט" — הצעד הראשון</div>
    <div class="bubcap__s" id="annexCapSub">צו צבאי שמסמן שטח להקמת התנחלות עתידית</div>
  </div>
  <p class="src-line" style="color:#8a8a84">מקור: [ מקור — להשלמה ]</p>
</div>
```

```js
/* ---- ANNEXATION (jurisdiction orders — rate comparison) ---- */
(function(){
  var wrap=document.getElementById('rateBars'); if(!wrap) return;
  var cap=document.getElementById('annexCap'), sub=document.getElementById('annexCapSub');
  var bars=wrap.querySelectorAll('.ratebar');
  var S=[
    {n:0, t:'"שטח שיפוט" — הצעד הראשון', s:'צו צבאי שמסמן שטח להקמת התנחלות עתידית'},
    {n:1, t:'114 צווים — ב-22 שנה', s:'2001–2022: כ-5 צווים בשנה'},
    {n:2, t:'114 צווים — ב-3 שנים', s:'2023–2026: כ-38 צווים בשנה — פי 7 בקצב'},
    {n:2, t:'53 התנחלויות · 25,295 דונם', s:'נכנסו לשיפוט ישראלי — תפיסה מינהלית בלי דיון ציבורי או ערעור'}
  ];
  var cur=-1;
  function show(i){ if(i===cur)return; cur=i; var s=S[i]||S[0];
    bars.forEach(function(b,bi){ b.classList.toggle('in', bi < s.n); });
    cap.textContent=s.t; sub.textContent=s.s; }
  show(0);
  scrolly('#annexSteps', show);
})();
```

---

## ציר זמן (chronology)

טבלת אירועים בשתי עמודות (תאריך / אירוע) מקובצת ל"עידנים", עם קישורי "קראו אצלנו".

```css
/* chronology */
.chrono{margin:30px 0 0; border-top:2px solid var(--ink)}
.chrono__row{display:grid; grid-template-columns:130px 1fr; gap:clamp(14px,3vw,28px); padding:20px 2px; border-bottom:1px solid var(--line); align-items:baseline}
.chrono__date{font-family:"Suez One",serif; color:var(--terra-deep); font-size:1.05rem; font-variant-numeric:tabular-nums; line-height:1.3}
.chrono__ev{margin:0; line-height:1.6}
.chrono__ev b{display:block; margin-bottom:3px; font-size:1.05rem}
.chrono__ev span{color:#6b6b66; font-size:.96rem}
@media(max-width:560px){.chrono__row{grid-template-columns:1fr; gap:4px} .netmap{overflow-x:auto;-webkit-overflow-scrolling:touch} .netmap svg{min-width:460px} .net__node text{font-size:18px}}

/* chronology coverage link */
.chrono__src{display:inline-block; margin-top:7px; font-size:.9rem; font-weight:600; color:var(--terra-deep); text-decoration:none; border-bottom:1px solid rgba(217,119,87,.35)}
.chrono__src:hover{border-bottom-color:var(--terra-deep)}
.chrono__src::after{content:" \2190"}
.chrono__era{padding:22px 2px 6px; font-family:"Suez One",serif; color:#8a8a84; font-size:.95rem; letter-spacing:.04em}
```

```html
<section class="sec">
  <div class="wrap narrow">
    <p class="kicker reveal">ציר זמן</p>
    <h2 class="reveal" style="max-width:22ch">[ כותרת־משנה — להשלמה ]</h2>
    <p class="lead reveal" style="margin-bottom:8px">[ שורת הקשר — להשלמה ]</p>
    <div class="chrono reveal">

      <div class="chrono__era">[ שם עידן — להשלמה ]</div>
      <div class="chrono__row"><div class="chrono__date">1967</div><p class="chrono__ev"><b>[ כותרת אירוע ]</b><span>[ תיאור האירוע — להשלמה ]</span></p></div>
      <div class="chrono__row"><div class="chrono__date">1981</div><p class="chrono__ev"><b>[ כותרת אירוע ]</b><span>[ תיאור ] <a class="chrono__src" href="[ URL כתבה ]" target="_blank" rel="noopener">קראו אצלנו</a></span></p></div>

      <div class="chrono__era">[ שם עידן נוסף — להשלמה ]</div>
      <div class="chrono__row"><div class="chrono__date">2025</div><p class="chrono__ev"><b>[ כותרת אירוע ]</b><span>[ תיאור ] <a class="chrono__src" href="[ URL כתבה ]" target="_blank" rel="noopener">קראו אצלנו</a></span></p></div>

    </div>
  </div>
</section>
```

הערה: אין JS ייעודי — האנימציה מגיעה מ-class `reveal` שעליו פועל ה-IIFE הגנרי של reveal-on-scroll. מבנה הציר המלא (כל האירועים) נמצא במקור yosh בשורות 752–773.

---

## רשת מושגים (concept network graph)

גרף כוח: צמתים עגולים מחוברים בקווים; לחיצה על צומת מדגישה שכנים ומציגה הגדרה ב-`#glossDef`.

```css
/* concept network (balls + links) */
.netmap{width:100%; margin:24px 0 18px; background:var(--paper); border:1px solid var(--line); border-radius:18px; padding:8px}
.netmap svg{width:100%; height:auto; display:block; touch-action:manipulation}
.net__edge{stroke:#cfccc0; stroke-width:1.5; transition:stroke .2s, stroke-width .2s, opacity .2s}
.net__edge.on{stroke:var(--terra); stroke-width:2.5}
.net__edge.fade{opacity:.3}
.net__node{cursor:pointer}
.net__node circle{stroke:#fff; stroke-width:2; transition:opacity .2s, stroke .2s, stroke-width .2s}
.net__node text{font-family:"IBM Plex Sans Hebrew",sans-serif; font-weight:600; font-size:15px; fill:var(--ink); pointer-events:none; text-anchor:middle}
.net__node.dim{opacity:.32}
.net__node.sel circle{stroke:var(--ink); stroke-width:3.5}
.net__hint{font-family:"IBM Plex Sans Hebrew",sans-serif; font-size:.85rem; color:#8a8a84; margin:0 4px 14px}

/* כלל מובייל לרשת (חלק מ-@media(max-width:560px) המשותף עם chronology) */
@media(max-width:560px){.netmap{overflow-x:auto;-webkit-overflow-scrolling:touch} .netmap svg{min-width:460px} .net__node text{font-size:18px}}
```

```html
<section class="sec">
  <div class="wrap narrow">
    <p class="kicker reveal">מפת מושגים</p>
    <h2 class="reveal" style="max-width:24ch">[ כותרת־משנה — להשלמה ]</h2>
    <p class="lead reveal" style="margin-bottom:4px">[ שורת הקשר — להשלמה ]</p>
    <div class="reveal">
      <div class="netmap"><svg id="netSvg" viewBox="0 0 900 580" role="img" aria-label="רשת המושגים"></svg></div>
      <p class="net__hint">לחצו על צומת ברשת · הקווים מראים מי מזין את מי במנגנון</p>
      <div class="gloss__def" id="glossDef"><h4></h4><p></p></div>
    </div>
  </div>
</section>
```

```js
/* ---- CONCEPT NETWORK (balls + links) ---- */
(function(){
  var svg=document.getElementById('netSvg'), def=document.getElementById('glossDef');
  if(!svg||!def) return;
  var NS='http://www.w3.org/2000/svg';
  var TERRA='#D97757', TERRAD='#D97757', SAGE='#788C5D', HEATHER='#8E6FA8';
  var N=[
    {id:'plan', x:450,y:300,r:46,c:TERRAD, t:'מערכת התכנון', d:'[ הגדרה — להשלמה ]'},
    {id:'areaC', x:225,y:150,r:38,c:TERRA, t:'שטח C', d:'[ הגדרה — להשלמה ]'},
    {id:'civ', x:450,y:125,r:40,c:SAGE, t:'המנהל האזרחי', d:'[ הגדרה — להשלמה ]'},
    {id:'council', x:690,y:160,r:40,c:SAGE, t:'מועצת התכנון', d:'[ הגדרה — להשלמה ]'},
    {id:'land', x:185,y:320,r:38,c:TERRA, t:'אדמת מדינה', d:'[ הגדרה — להשלמה ]'},
    {id:'settle', x:715,y:330,r:44,c:TERRAD, t:'התנחלות', d:'[ הגדרה — להשלמה ]'},
    {id:'outpost',x:700,y:480,r:34,c:HEATHER, t:'מאחז', d:'[ הגדרה — להשלמה ]'},
    {id:'hasdara',x:490,y:485,r:34,c:HEATHER, t:'הסדרה', d:'[ הגדרה — להשלמה ]'},
    {id:'exempt', x:255,y:475,r:34,c:SAGE, t:'פטור ממכרז', d:'[ הגדרה — להשלמה ]'},
    {id:'order',  x:135,y:455,r:34,c:TERRA, t:'צו שיפוט', d:'[ הגדרה — להשלמה ]'}
  ];
  var E=[['plan','areaC'],['plan','civ'],['civ','council'],['plan','council'],['council','settle'],['council','land'],['land','settle'],['areaC','land'],['settle','outpost'],['outpost','hasdara'],['hasdara','settle'],['settle','exempt'],['plan','order'],['order','settle']];
  function byId(id){for(var i=0;i<N.length;i++)if(N[i].id===id)return N[i];}
  function neigh(id){var s={};E.forEach(function(e){if(e[0]===id)s[e[1]]=1;if(e[1]===id)s[e[0]]=1;});return s;}
  var edgeEls=[], nodeEls={};
  E.forEach(function(e){var a=byId(e[0]),b=byId(e[1]);var l=document.createElementNS(NS,'line');l.setAttribute('x1',a.x);l.setAttribute('y1',a.y);l.setAttribute('x2',b.x);l.setAttribute('y2',b.y);l.setAttribute('class','net__edge');l._a=e[0];l._b=e[1];svg.appendChild(l);edgeEls.push(l);});
  N.forEach(function(n){
    var g=document.createElementNS(NS,'g');g.setAttribute('class','net__node');g.setAttribute('tabindex','0');g.setAttribute('role','button');g.setAttribute('aria-label',n.t);
    var c=document.createElementNS(NS,'circle');c.setAttribute('cx',n.x);c.setAttribute('cy',n.y);c.setAttribute('r',n.r);c.setAttribute('fill',n.c);
    var t=document.createElementNS(NS,'text');t.setAttribute('x',n.x);t.setAttribute('y',n.y+n.r+17);t.textContent=n.t;
    g.appendChild(c);g.appendChild(t);
    g.addEventListener('click',function(){sel(n.id);});
    g.addEventListener('keydown',function(ev){if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();sel(n.id);}});
    svg.appendChild(g);nodeEls[n.id]=g;
  });
  function sel(id){
    var ns=neigh(id);
    N.forEach(function(n){var g=nodeEls[n.id];var rel=(n.id===id||ns[n.id]);g.classList.toggle('dim',!rel);g.classList.toggle('sel',n.id===id);});
    edgeEls.forEach(function(l){var on=(l._a===id||l._b===id);l.classList.toggle('on',on);l.classList.toggle('fade',!on);});
    var nd=byId(id);def.querySelector('h4').textContent=nd.t;def.querySelector('p').textContent=nd.d;
  }
  sel('plan');
})();
```

הערה: ה-`<h4>`/`<p>` בתוך `#glossDef` הם גם תיבת ההגדרה של רשת המושגים (הקומפוננטה משתמשת ב-CSS של `.gloss__def`).

---

## שו״ת (FAQ)

אקורדיון `<details>` נגיש + סקריפט `FAQPage` (JSON-LD) ל-SEO/AEO — שכפלו פריט לכל שאלה ושמרו על זהות הטקסט בין ה-HTML ל-JSON.

```css
/* FAQ / practical guide (accordion) */
.faq{margin:26px 0 0; border-top:2px solid var(--ink)}
.faq__item{border-bottom:1px solid var(--line)}
.faq__item summary{list-style:none; cursor:pointer; padding:20px 2px; font-family:"IBM Plex Sans Hebrew",sans-serif; font-weight:700; font-size:1.1rem; display:flex; justify-content:space-between; gap:16px; align-items:center}
.faq__item summary::-webkit-details-marker{display:none}
.faq__item summary::after{content:"+"; color:var(--terra); font-family:"Suez One",serif; font-size:1.5rem; line-height:1; flex:0 0 auto}
.faq__item[open] summary::after{content:"\2212"}
.faq__item p{margin:0 2px 24px; line-height:1.75; color:#46443f; font-size:1.05rem; max-width:64ch}
```

```html
<section class="sec">
  <div class="wrap narrow">
    <p class="kicker reveal">שאלות ותשובות</p>
    <h2 class="reveal" style="max-width:24ch">[ כותרת־משנה — להשלמה ]</h2>
    <div class="faq reveal">
      <details class="faq__item"><summary>[ שאלה — להשלמה ]</summary><p>[ תשובה — להשלמה ]</p></details>
      <details class="faq__item"><summary>[ שאלה — להשלמה ]</summary><p>[ תשובה — להשלמה ]</p></details>
      <!-- שכפלו פריט לכל שאלה -->
    </div>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
      {"@type":"Question","name":"[ שאלה — להשלמה ]","acceptedAnswer":{"@type":"Answer","text":"[ תשובה — להשלמה ]"}},
      {"@type":"Question","name":"[ שאלה — להשלמה ]","acceptedAnswer":{"@type":"Answer","text":"[ תשובה — להשלמה ]"}}
    ]}
    </script>
  </div>
</section>
```

דוגמת מקור (yosh) לעיון, שמירה על מבנה ה-JSON-LD:

```html
<details class="faq__item"><summary>מהו שטח C ומי שולט בו?</summary><p>שטח C הוא כ-60% משטח הגדה המערבית, בשליטה אזרחית וביטחונית ישראלית מלאה לפי הסכמי אוסלו (1995). בשטח C יושבות כל ההתנחלויות, ושם מתנהלת מערכת התכנון הישראלית שמכריעה מי רשאי לבנות.</p></details>
```

---

## מילון מונחים (glossary)

צ׳יפים נבחרים שמחליפים הגדרה בתיבה. בעמוד yosh ה-CSS קיים אך מנוצל חלקית — `.gloss__def` משמש את רשת המושגים, וה-`.gloss__terms`/`.gloss__term` זמינים למילון עצמאי (ללא JS במקור; מימוש לדוגמה למטה).

```css
/* interactive glossary */
.gloss__terms{display:flex; flex-wrap:wrap; gap:10px; margin:26px 0 20px}
.gloss__term{font-family:"IBM Plex Sans Hebrew",sans-serif; font-size:.98rem; padding:10px 18px; border:1px solid var(--line); border-radius:999px; background:var(--ivory); color:var(--ink); cursor:pointer; transition:background .2s,color .2s,border-color .2s}
.gloss__term:hover{border-color:var(--terra)}
.gloss__term.on{background:var(--terra); color:#fff; border-color:var(--terra)}
.gloss__def{background:var(--paper); border:1px solid var(--line); border-radius:16px; padding:26px clamp(20px,4vw,32px); min-height:96px}
.gloss__def h4{margin:0 0 10px; font-family:"Suez One",serif; color:var(--terra-deep); font-size:1.2rem}
.gloss__def p{margin:0; line-height:1.7; font-size:1.05rem}
```

```html
<div class="gloss__terms" id="glossTerms">
  <button class="gloss__term" data-k="0">[ מונח — להשלמה ]</button>
  <button class="gloss__term" data-k="1">[ מונח — להשלמה ]</button>
</div>
<div class="gloss__def" id="glossBox"><h4></h4><p></p></div>
```

```js
/* מימוש מילון עצמאי (לא קיים במקור yosh — תבנית לשימוש חוזר) */
(function(){
  var box=document.getElementById('glossBox'); if(!box) return;
  var G=[
    {t:'[ מונח — להשלמה ]', d:'[ הגדרה — להשלמה ]'},
    {t:'[ מונח — להשלמה ]', d:'[ הגדרה — להשלמה ]'}
  ];
  var btns=document.querySelectorAll('#glossTerms .gloss__term');
  function pick(k){ btns.forEach(function(b){b.classList.toggle('on',+b.dataset.k===k);});
    box.querySelector('h4').textContent=G[k].t; box.querySelector('p').textContent=G[k].d; }
  btns.forEach(function(b){ b.addEventListener('click',function(){pick(+b.dataset.k);}); });
  pick(0);
})();
```

---

## דירוגים (ranks)

ברים אופקיים ממוינים (top-N) שרוחבם יחסי לערך; מתמלאים כשהבלוק נכנס למסך (class `reveal` → `.ranks.in`).

```css
/* ---------- ranks (settlements by units) ---------- */
.ranks{max-width:620px; margin:18px auto 0}
.rank{display:grid; grid-template-columns:8.5em 1fr 4.2em; align-items:center; gap:10px; margin:8px 0}
.rank__name{font-size:.92rem; color:var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
.rank__track{height:15px; background:var(--paper); border:1px solid var(--line); border-radius:3px; overflow:hidden}
.rank__bar{display:block; height:100%; background:var(--terra); border-radius:0 2px 2px 0; transform-origin:right; transform:scaleX(0); transition:transform .9s cubic-bezier(.2,.8,.2,1)}
.ranks.in .rank__bar{transform:scaleX(1)}
.rank__val{font-size:.82rem; color:#6b6b66; font-variant-numeric:tabular-nums; text-align:left}
```

```html
<div class="ranks reveal">
  <div class="rank"><span class="rank__name">[ שם — להשלמה ]</span><span class="rank__track"><span class="rank__bar" style="width:100%"></span></span><span class="rank__val">10,693</span></div>
  <div class="rank"><span class="rank__name">[ שם — להשלמה ]</span><span class="rank__track"><span class="rank__bar" style="width:95.7%"></span></span><span class="rank__val">10,232</span></div>
  <!-- חזרו לכל שורה; width = ערך/מקסימום * 100% -->
</div>
```

הערה: אין JS ייעודי — class `reveal` מוסיף `in` שמפעיל את אנימציית `scaleX`.

---

## מפת Leaflet

מפה אינטראקטיבית עם spine של scrolly: כל צעד ממסגר אזור (frame) ומדליק/מכבה שכבות. הנתונים נטענים יחסית מתיקיית האפליקציה (`app/`).

חשוב — קבצי הנתונים הבאים הם yosh-ספציפיים ויש להחליפם `[ נתונים — להשלמה ]`:
`plans.geojson`, `settlements.geojson`, `layers/area_a.geojson`, `layers/area_b.geojson`, `layers/area_c.geojson`, `layers/declared_state_land.geojson`, `layers/firing_zones.geojson`, `layers/nature_reserves.geojson`, `layers/israeli_agriculture.geojson`, `wb-core-articles.json`. כולם נטענים בנתיב יחסי (fetch) — בעת אריזה כתוסף ודאו שהם יושבים תחת `app/`, ו-Leaflet (CSS+JS) מקומי (`vendor/leaflet/...`) ולא CDN.

```html
<!-- מפה ראשית -->
<div class="scrolly__graphic">
  <div id="wbmap"></div>
  <div class="maplbl">
    <span><i style="background:var(--terra)"></i>תוכנית התנחלות</span>
    <span><i style="background:var(--heather)"></i>תוכנית פלסטינית</span>
  </div>
  <div class="chips" id="mapChips" aria-label="שכבות נתונים על המפה"></div>
</div>

<!-- מפה שנייה (אופציונלי) -->
<div class="scrolly__graphic">
  <div id="farmmap"></div>
  <div class="maplbl"><span><i style="background:#9C8A4A;border-radius:2px"></i>חוות חקלאיות</span><span><i style="background:#C2562F;border-radius:2px"></i>שטחי אש</span><span><i style="background:#D97757;border-radius:2px"></i>אדמת מדינה</span></div>
</div>
```

CSS נדרש (קונטיינרים, תוויות, צ׳יפים):

```css
/* ---------- map ---------- */
#wbmap,#farmmap{width:100%; height:88vh; max-height:820px; border-radius:14px; border:1px solid var(--line); background:var(--paper)}
.maplbl{display:flex; gap:16px; flex-wrap:wrap; margin-top:14px; font-size:.84rem; color:#3a3a37}
.maplbl i{width:13px;height:13px;border-radius:50%;display:inline-block;margin-inline-end:6px;vertical-align:-2px}
.chips{display:flex; flex-wrap:wrap; gap:7px; margin-top:14px}
.chip{font-family:inherit; font-size:.8rem; cursor:pointer; border:1px solid var(--line); background:#fff; color:#3a3a37; border-radius:999px; padding:5px 12px; display:inline-flex; align-items:center; gap:6px; transition:background-color .15s,border-color .15s,color .15s}
.chip i{width:10px;height:10px;border-radius:2px;display:inline-block}
.chip[aria-pressed=true]{background:var(--ink); color:var(--ivory); border-color:var(--ink)}
.chip:hover{border-color:var(--ink)}
.chip:focus-visible{outline:2px solid var(--terra); outline-offset:2px}
```

```js
/* ---- MAP (Leaflet, scrolly spine) ---- */
function mapFallback(id){var el=document.getElementById(id);if(el)el.innerHTML='<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#8a8a84;font-size:.92rem;text-align:center;padding:24px;line-height:1.5">המפה האינטראקטיבית לא נטענה.<br>נסו לרענן את העמוד.</div>';}
(function(){
  if(!window.L){ mapFallback('wbmap'); return; }
  var WB=L.latLngBounds([[31.34,34.86],[32.56,35.62]]);
  var E1=L.latLngBounds([[31.73,35.22],[31.86,35.42]]);
  var ARIEL=L.latLngBounds([[32.0,34.95],[32.22,35.28]]);
  var map=L.map('wbmap',{zoomControl:false,scrollWheelZoom:false,dragging:true,attributionControl:false,maxBounds:WB.pad(.3),maxBoundsViscosity:.7});
  function frame(b){map.invalidateSize();var t=b||WB;var z=map.getBoundsZoom(t,true);map.setView(t.getCenter(),z,{animate:true,duration:.8});}
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',{subdomains:'abcd',maxZoom:16}).addTo(map);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png',{subdomains:'abcd',maxZoom:16}).addTo(map);
  frame();
  var COL={jewish:'#D97757',palestinian:'#8E6FA8',infrastructure_regional:'#788C5D',unknown:'#b9b6ab'};
  var layers={jewish:L.layerGroup(),palestinian:L.layerGroup(),other:L.layerGroup()};
  fetch('plans.geojson').then(function(r){return r.json();}).then(function(gj){
    (gj&&gj.features||[]).forEach(function(f){
      if(!f||!f.geometry||!f.geometry.coordinates) return;
      var p=f.properties||{},c=f.geometry.coordinates,u=+p.u||0;
      var g=(p.sec==='jewish')?layers.jewish:(p.sec==='palestinian')?layers.palestinian:layers.other;
      L.circleMarker([c[1],c[0]],{radius:Math.max(4,Math.min(18,4+Math.sqrt(u)*0.95)),color:'#fff',weight:1,fillColor:COL[p.sec]||COL.unknown,fillOpacity:.85})
        .bindPopup('<b>'+(p.name||p.n||'תוכנית')+'</b><br>'+(p.place||'')+(u?'<br>'+u+' יח״ד':'')).addTo(g);
    });
    show(['jewish','palestinian','other']); setTimeout(function(){frame();},300);
  }).catch(function(){ show(['jewish','palestinian','other']); frame(); });
  function show(list){for(var k in layers){if(list.indexOf(k)>=0)layers[k].addTo(map);else map.removeLayer(layers[k]);}}

  // ---- all context overlay layers (lazy-loaded, chip-toggleable) ----
  var ATLAS={
    settlements:{file:'settlements.geojson',markers:true,color:'#141413',label:'יישובים'},
    area_a:{file:'layers/area_a.geojson',color:'#788C5D',fill:.20,label:'שטח A'},
    area_b:{file:'layers/area_b.geojson',color:'#8E6FA8',fill:.16,label:'שטח B'},
    area_c:{file:'layers/area_c.geojson',color:'#D97757',fill:.13,label:'שטח C'},
    state_land:{file:'layers/declared_state_land.geojson',color:'#D97757',fill:.42,label:'אדמת מדינה'},
    firing:{file:'layers/firing_zones.geojson',color:'#C2562F',fill:.12,dash:'5 4',label:'שטחי אש'},
    nature:{file:'layers/nature_reserves.geojson',color:'#5E7344',fill:.20,label:'שמורות טבע'},
    agri:{file:'layers/israeli_agriculture.geojson',color:'#9C8A4A',fill:.22,label:'חוות חקלאיות'}
  };
  var built={}, onL={};
  function build(key,gj){var c=ATLAS[key];
    if(c.markers)return L.geoJSON(gj,{pointToLayer:function(f,ll){return L.circleMarker(ll,{radius:3,color:'#fff',weight:.6,fillColor:c.color,fillOpacity:.7});},
      onEachFeature:function(f,l){var p=f.properties||{};var nm=p.name||p.Name||p.SHEM_YISH||p.title||'';if(nm)l.bindPopup(nm);}});
    return L.geoJSON(gj,{style:{color:c.color,weight:1,fillColor:c.color,fillOpacity:c.fill,dashArray:c.dash||null}});}
  function setLayer(key,on){ onL[key]=on;
    var chip=document.querySelector('#mapChips [data-layer="'+key+'"]'); if(chip)chip.setAttribute('aria-pressed',on?'true':'false');
    if(on){ if(built[key]){built[key].addTo(map);} else { fetch(ATLAS[key].file).then(function(r){return r.json();}).then(function(gj){ built[key]=build(key,gj); if(onL[key])built[key].addTo(map); }).catch(function(){}); } }
    else if(built[key]){ map.removeLayer(built[key]); } }
  function only(keys){ Object.keys(ATLAS).forEach(function(k){ setLayer(k, keys.indexOf(k)>=0); }); }
  var chipsBox=document.getElementById('mapChips');
  if(chipsBox)Object.keys(ATLAS).forEach(function(key){ var c=ATLAS[key];
    var b=document.createElement('button'); b.className='chip'; b.type='button'; b.dataset.layer=key; b.setAttribute('aria-pressed','false');
    b.innerHTML='<i style="background:'+c.color+'"></i>'+c.label;
    b.addEventListener('click',function(){ setLayer(key, b.getAttribute('aria-pressed')!=='true'); });
    chipsBox.appendChild(b); });

  scrolly('#mapSteps', function(i){
    if(i===0){ only([]); show(['jewish','palestinian','other']); frame(WB); }
    else if(i===1){ only([]); show(['jewish']); frame(WB); }
    else if(i===2){ only([]); show(['palestinian']); frame(WB); }
    else if(i===3){ only(['area_c']); show(['jewish','palestinian','other']); frame(WB); }
    else if(i===4){ only(['state_land']); show(['jewish','palestinian','other']); frame(WB); }
    else if(i===5){ only(['firing']); show(['jewish','palestinian','other']); frame(WB); }
    else if(i===6){ only(['area_c']); show(['jewish','palestinian','other']); frame(E1); }
    else if(i===7){ only([]); show(['jewish','palestinian','other']); frame(ARIEL); }
  });
  var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){frame();io.disconnect();}});},{threshold:.2});
  io.observe(document.getElementById('wbmap'));
})();

/* ---- FARM MAP (second map appearance) ---- */
(function(){
  if(!document.getElementById('farmmap')) return;
  if(!window.L){ mapFallback('farmmap'); return; }
  var WB=L.latLngBounds([[31.34,34.86],[32.56,35.62]]);
  var JV=L.latLngBounds([[31.82,35.28],[32.42,35.58]]);
  var SH=L.latLngBounds([[31.28,34.92],[31.58,35.20]]);
  var map=L.map('farmmap',{zoomControl:false,scrollWheelZoom:false,dragging:true,attributionControl:false,maxBounds:WB.pad(.3),maxBoundsViscosity:.7});
  function frame(b){map.invalidateSize();var t=b||WB;var z=map.getBoundsZoom(t,true);map.setView(t.getCenter(),z,{animate:true,duration:.8});}
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',{subdomains:'abcd',maxZoom:16}).addTo(map);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png',{subdomains:'abcd',maxZoom:16}).addTo(map);
  frame();
  var fl={};
  function fload(key,file,style,on){
    if(fl[key]){ if(on)fl[key].addTo(map); else map.removeLayer(fl[key]); return; }
    if(!on) return;
    fetch(file).then(function(r){return r.json();}).then(function(gj){ fl[key]=L.geoJSON(gj,{style:style}); if(on)fl[key].addTo(map); }).catch(function(){});
  }
  function ctx(firing,state){
    fload('agri','layers/israeli_agriculture.geojson',{color:'#9C8A4A',weight:.6,fillColor:'#9C8A4A',fillOpacity:.55},true);
    fload('firing','layers/firing_zones.geojson',{color:'#C2562F',weight:1,fillColor:'#C2562F',fillOpacity:.12,dashArray:'5 4'},firing);
    fload('state','layers/declared_state_land.geojson',{color:'#D97757',weight:1,fillColor:'#D97757',fillOpacity:.38},state);
  }
  scrolly('#farmSteps', function(i){
    if(i===0){ ctx(false,false); frame(WB); }
    else if(i===1){ ctx(true,false); frame(JV); }
    else if(i===2){ ctx(true,true); frame(JV); }
    else { ctx(true,false); frame(SH); }
  });
  var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){frame();io.disconnect();}});},{threshold:.2});
  io.observe(document.getElementById('farmmap'));
})();
```

---

## קנבס כוכבים (hero star canvas)

נקודות-תכנון נסחפות ברקע ה-HERO על `<canvas id="heroCanvas">`. כבר משובץ ב-template/index.html — מובא כאן לעיון בלבד; מכבד `prefers-reduced-motion` ועוצר כשה-hero מחוץ למסך.

```js
/* ---- HERO ambient canvas (drifting plan-dots) ---- */
(function(){
  var cv=document.getElementById('heroCanvas'); if(!cv||REDUCE)return;
  var ctx=cv.getContext('2d'), W,H,pts=[];
  function size(){W=cv.width=cv.offsetWidth; H=cv.height=cv.offsetHeight;
    pts=[]; var n=Math.floor(W*H/9000);
    for(var i=0;i<n;i++)pts.push({x:Math.random()*W,y:Math.random()*H,r:Math.random()*2+1,
      vx:(Math.random()-.5)*.25,vy:(Math.random()-.5)*.25,c:Math.random()<.78?'#D97757':'#8E6FA8'});}
  size(); window.addEventListener('resize',size);
  var raf=null, vis=true;
  function loop(){ if(!vis){raf=null;return;}
    ctx.clearRect(0,0,W,H);
    pts.forEach(function(p){p.x+=p.vx;p.y+=p.vy;
      if(p.x<0||p.x>W)p.vx*=-1; if(p.y<0||p.y>H)p.vy*=-1;
      ctx.globalAlpha=.5; ctx.fillStyle=p.c; ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,7); ctx.fill();});
    raf=requestAnimationFrame(loop);
  }
  if(window.IntersectionObserver){ new IntersectionObserver(function(es){ vis=es[0].isIntersecting; if(vis&&!raf)loop(); }).observe(cv); }
  loop();
})();
```
