#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_timeline_embed.py — מפיק ציר זמן אינטראקטיבי להטמעה בוורדפרס.

CSS בלבד (radio + :checked) — בלי <script>, כי וורדפרס מסנן סקריפטים בצד הקדמי.
ממודר לחלוטין: all:initial על השורש + prefix ייחודי, כך שכלום לא דולף לעיצוב האתר.
כולל <meta charset> בראש כדי שהקובץ יוצג נכון גם כקובץ עצמאי.

שימוש:
  python3 build_timeline_embed.py events.json -o embed.html [--footer "מקור: ..."] [--accent "#cc785c"] [--prefix hmtl]

events.json: [{"date": "...", "label": "2-4 מילים", "title": "...", "body": "..."}, ...]
התחנה האחרונה נבחרת כברירת מחדל.
"""
import json, argparse, sys
from html import escape as _esc


def esc(v):
    """HTML-escape לשדה אירוע: <, >, & ומרכאות. שדות האירוע הם טקסט, לא HTML -
    בלי זה `<` או `&` בגוף האירוע שוברים את ההטמעה או מזריקים תגיות."""
    return _esc(str(v), quote=True)

def build(events, footer, accent, accent_deep, prefix, hint):
    n = len(events); last = n - 1
    p = prefix
    def join(fmt): return ", ".join(fmt.format(i=i, p=p) for i in range(n))
    rules = "".join([
        join("#{p}-r{i}:checked~.{p}-cards .{p}-c{i}") + "{display:block}",
        join("#{p}-r{i}:checked~.{p}-railwrap .{p}-n{i} .{p}-dot") + "{background:%s;border-color:%s;transform:scale(1.3)}" % (accent, accent),
        join("#{p}-r{i}:checked~.{p}-railwrap .{p}-n{i} .{p}-d") + "{color:%s}" % accent_deep,
        join("#{p}-r{i}:checked~.{p}-railwrap .{p}-n{i} .{p}-l") + "{color:#1f1e1d;font-weight:500}",
        join("#{p}-r{i}:focus-visible~.{p}-railwrap .{p}-n{i} .{p}-dot") + "{outline:2px solid %s;outline-offset:2px}" % accent,
    ])
    style = (
        ".{p}{{all:initial;display:block;width:100%;max-width:100%;box-sizing:border-box;"
        "font-family:system-ui,-apple-system,'Segoe UI',Arial,sans-serif;color:#1f1e1d;direction:rtl;margin:0;padding:8px 0 4px}}"
        ".{p} *{{box-sizing:border-box;margin:0;padding:0}}"
        ".{p}-radio{{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}}"
        ".{p}-hint{{font-size:13px;color:#6b6a64;margin:0 0 14px}}"
        ".{p}-railwrap{{overflow-x:auto;overflow-y:hidden;padding:4px 2px 14px}}"
        ".{p}-railwrap::-webkit-scrollbar{{height:7px}}"
        ".{p}-railwrap::-webkit-scrollbar-thumb{{background:{a};border-radius:4px}}"
        ".{p}-rail{{position:relative;display:flex;min-width:max-content;padding:0 6px}}"
        ".{p}-base{{position:absolute;top:42px;right:6px;left:6px;height:2px;background:rgba(31,30,29,.14);border-radius:2px}}"
        ".{p}-node{{position:relative;z-index:1;width:116px;flex:0 0 116px;text-align:center;cursor:pointer}}"
        ".{p}-node .{p}-d{{display:flex;align-items:flex-end;justify-content:center;height:28px;font-size:12px;font-weight:500;color:#6b6a64;transition:color .2s}}"
        ".{p}-node .{p}-dot{{display:block;width:15px;height:15px;border-radius:50%;background:#fff;border:2px solid rgba(31,30,29,.32);margin:7px auto 9px;transition:all .2s}}"
        ".{p}-node .{p}-l{{display:block;font-size:12.5px;line-height:1.35;color:#6b6a64;padding:0 5px;transition:color .2s}}"
        ".{p}-node:hover .{p}-dot{{border-color:{a}}}"
        ".{p}-node:hover .{p}-l{{color:#1f1e1d}}"
        ".{p}-cards{{margin-top:18px}}"
        ".{p}-card{{display:none;background:#f0eee6;border-radius:12px;padding:16px 20px;border-right:3px solid {a}}}"
        ".{p}-card .{p}-cd{{font-size:13px;font-weight:500;color:{ad};margin-bottom:6px}}"
        ".{p}-card .{p}-ct{{font-size:18px;font-weight:500;line-height:1.3;margin-bottom:10px}}"
        ".{p}-card .{p}-cb{{font-size:16px;line-height:1.7;color:#4a4843}}"
        ".{p}-foot{{margin-top:16px;font-size:12px;color:#6b6a64}}"
    ).format(p=p, a=accent, ad=accent_deep) + rules
    radios = "".join(
        '<input class="{p}-radio" type="radio" name="{p}" id="{p}-r{i}"{c}>'.format(p=p, i=i, c=" checked" if i == last else "")
        for i in range(n))
    nodes = "".join(
        '<label class="{p}-node {p}-n{i}" for="{p}-r{i}"><span class="{p}-d">{d}</span><span class="{p}-dot"></span><span class="{p}-l">{l}</span></label>'.format(
            p=p, i=i, d=esc(e["date"]), l=esc(e["label"])) for i, e in enumerate(events))
    cards = "".join(
        '<div class="{p}-card {p}-c{i}"><div class="{p}-cd">{d}</div><div class="{p}-ct">{t}</div><div class="{p}-cb">{b}</div></div>'.format(
            p=p, i=i, d=esc(e["date"]), t=esc(e["title"]), b=esc(e["body"]))
        for i, e in enumerate(events))
    return (
        '<meta charset="utf-8">\n<div class="{p}">\n<style>{s}</style>\n{r}\n'
        '<div class="{p}-hint">{h}</div>\n'
        '<div class="{p}-railwrap"><div class="{p}-rail"><span class="{p}-base"></span>{n}</div></div>\n'
        '<div class="{p}-cards">{c}</div>\n'
        '<div class="{p}-foot">{f}</div>\n</div>\n'
    ).format(p=p, s=style, r=radios, h=hint, n=nodes, c=cards, f=footer)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("events_json")
    ap.add_argument("-o", "--out", default="timeline-embed.html")
    ap.add_argument("--footer", default="")
    ap.add_argument("--accent", default="#cc785c")
    ap.add_argument("--accent-deep", default="#8a4a30")
    ap.add_argument("--prefix", default="hmtl")
    ap.add_argument("--hint", default="לחצו על תחנה בציר כדי לקרוא מה קרה בה")
    args = ap.parse_args()
    with open(args.events_json, encoding="utf-8") as f:
        events = json.load(f)
    if not 2 <= len(events) <= 20:
        sys.exit("between 2 and 20 events please")
    for e in events:
        for k in ("date", "label", "title", "body"):
            if k not in e: sys.exit("missing key %r in event: %r" % (k, e))
        for k in ("date", "label", "title", "body"):
            if not isinstance(e[k], str): sys.exit("field %r must be a string in event: %r" % (k, e))
            if '"' in e[k]: sys.exit('ASCII double quote in %r - use ״ (gershayim) or “ ” instead' % e[k][:40])
    html = build(events, args.footer, args.accent, args.accent_deep, args.prefix, args.hint)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", args.out, len(html.encode("utf-8")), "bytes; paste into a WordPress Custom HTML block")

if __name__ == "__main__":
    main()
