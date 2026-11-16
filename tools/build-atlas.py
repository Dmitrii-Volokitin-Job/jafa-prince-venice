#!/usr/bin/env python3
"""Builds atlas.html (the design atlas) from the live site.

Tokens and component CSS are read straight from index.html, so the atlas
can't drift from the site. Run:  python3 tools/build-atlas.py
"""
import re, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
site = (ROOT / 'index.html').read_text()
css = re.search(r'<style>(.*?)</style>', site, re.S).group(1)

def block(sel):
    m = re.search(re.escape(sel) + r'\{(.*?)\}', css, re.S)
    return dict(re.findall(r'--([\w-]+):\s*([^;]+);', m.group(1))) if m else {}

base = block(':root')
skins = {'dark': {k: v for k, v in base.items() if not k.startswith('sa')}}
for sk in ['light', 'laguna', 'terracotta', 'contrast']:
    t = dict(skins['dark']); t.update(block(f'[data-theme="{sk}"]')); skins[sk] = t
for t in skins.values():
    for k in ('sat', 'sab'): t.pop(k, None)

tpl = (ROOT / 'tools' / 'atlas-template.html').read_text()
out = (tpl.replace('/*SITE_CSS*/', css)
          .replace('/*TOKENS*/', 'const TOKENS=' + json.dumps(skins, ensure_ascii=False) + ';'))
(ROOT / 'atlas.html').write_text(out)
print('atlas.html written:', len(skins), 'skins,', len(skins['dark']), 'tokens each')
