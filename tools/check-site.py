import asyncio, json, sys
from playwright.async_api import async_playwright
BASE='http://localhost:8765/'
JS_LAYOUT = """() => {
 const out=[]; const r=s=>{const e=document.querySelector(s);return e&&e.getBoundingClientRect()};
 const mini=document.querySelector('#room .mini');
 if(mini){ const m=mini.getBoundingClientRect(); const svg=mini.querySelector('svg');
   if(svg){const sv=svg.getBoundingClientRect(); if(sv.height<100||sv.width<100) out.push('plan too small '+Math.round(sv.width)+'x'+Math.round(sv.height));
     const nxt=mini.nextElementSibling; if(nxt){const n=nxt.getBoundingClientRect(); const mob=innerWidth<760;
       if(mob && n.top < sv.bottom-1) out.push('plan overlaps content by '+Math.round(sv.bottom-n.top)+'px');
       if(!mob && n.left < sv.right-1) out.push('plan overlaps content horizontally');}} }
 if(document.documentElement.scrollWidth>innerWidth+1) out.push('horizontal scroll '+document.documentElement.scrollWidth);
 document.querySelectorAll('img').forEach(i=>{ if(i.complete && i.naturalWidth===0 && i.offsetParent) out.push('broken img '+i.getAttribute('src'))});
 return out; }"""
async def run(engine, vw, vh, lang='ru', theme='dark'):
    probs=[]
    b = await getattr(engine,'launch')()
    pg = await b.new_page(viewport={'width':vw,'height':vh})
    pg.on('pageerror', lambda e: probs.append('JS error: '+str(e)))
    pg.on('requestfailed', lambda r: (not r.url.startswith('https://fonts')) and 'ABORTED' not in (r.failure or '') and probs.append('failed '+r.url+' '+str(r.failure)))
    await pg.goto(BASE); await pg.click('#enter')
    await pg.evaluate(f"localStorage.setItem('hs-lang','{lang}');localStorage.setItem('hs-theme','{theme}')"); await pg.reload(); await pg.wait_for_timeout(300)
    if await pg.evaluate("document.documentElement.lang")!=lang: probs.append('lang not applied')
    ids = await pg.evaluate("({rooms:HS.rooms.map(r=>r.id),works:HS.works.map(w=>w.id),themes:Object.keys(HS.themes)})")
    for h in ['']+['map']+['room-'+i for i in ids['rooms']]+['thread-'+t for t in ids['themes']]+['work-'+w for w in ids['works']]:
        await pg.goto(BASE+'#'+h); await pg.wait_for_timeout(250)
        # load lazy images
        await pg.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager')"); await pg.wait_for_timeout(150)
        for p in await pg.evaluate(JS_LAYOUT): probs.append(f'#{h}: {p}')
        if lang=='ru':
            eng = await pg.evaluate(r'''() => { const vis=e=>e.offsetParent!==null; const bad=[];
              const root = document.querySelector('#modal.open .sbody') || [...document.querySelectorAll('main')].find(vis);
              const walk=document.createTreeWalker(root,NodeFilter.SHOW_TEXT); let n;
              while(n=walk.nextNode()){ const p=n.parentElement; if(!vis(p)||p.closest('h4,h3,i,.chip.sm,.rel,.works,.ytbtn,.vsrc,.gl')) continue;
                const tx=n.textContent.trim(); if(/\b(the|and|room|works?|of|with|in the|visit|photo|video)\b/i.test(tx) && !/[а-яё]/i.test(tx)) bad.push(tx.slice(0,60)); }
              return bad; }''')
            for e in eng: probs.append(f'#{h}: English text in RU: {e}')
        if h.startswith('work-'):
            ok = await pg.evaluate("document.querySelector('#modal').classList.contains('open') && document.querySelector('.sbody h3').textContent.length>0")
            if not ok: probs.append(f'#{h}: modal did not open')
            vids = await pg.evaluate("[...document.querySelectorAll('#modal video')].map(v=>v.getAttribute('src'))")
            for v in vids:
                st = await pg.evaluate(f"fetch('{v}',{{method:'HEAD'}}).then(r=>r.status)")
                if st!=200: probs.append(f'#{h}: video {v} {st}')
            if await pg.evaluate("!!document.querySelector('.vtabs')"):
                await pg.click('.vtabs button:nth-child(2)'); await pg.wait_for_timeout(100)
                if not await pg.evaluate("!!document.querySelector('.ytbtn')"): probs.append(f'#{h}: YouTube tab empty')
    # click-through: room nav and related cards
    await pg.goto(BASE+'#room-1'); await pg.wait_for_timeout(200)
    for i in range(16):
        await pg.click('.roomnav button:last-child'); await pg.wait_for_timeout(120)
    if await pg.evaluate("location.hash")!='#room-17': probs.append('next-room walk ended at '+await pg.evaluate("location.hash"))
    await pg.goto(BASE+'#work-graduation'); await pg.wait_for_timeout(200)
    await pg.click('.rel .card >> nth=0'); await pg.wait_for_timeout(200)
    if not (await pg.evaluate("location.hash")).startswith('#work-'): probs.append('related card click failed')
    await pg.click('.close'); await pg.wait_for_timeout(200)
    if await pg.evaluate("document.querySelector('#modal').classList.contains('open')"): probs.append('modal close failed')
    # home chips, artist chips, plan rooms
    await pg.goto(BASE); await pg.wait_for_timeout(200)
    n=await pg.evaluate("document.querySelectorAll('#themechips .chip').length")
    for i in range(n):
        await pg.goto(BASE); await pg.wait_for_timeout(120)
        await pg.click(f'#themechips .chip >> nth={i}'); await pg.wait_for_timeout(120)
        h=await pg.evaluate("location.hash"); c=await pg.evaluate("document.querySelectorAll('#threadwrap .works .card').length")
        if not h.startswith('#thread-') or c==0: probs.append(f'theme chip {i} -> {h} cards {c}')
    for sel in ['#ajlist .chip','#rplist .chip']:
        k=await pg.evaluate(f"document.querySelectorAll('{sel}').length")
        for i in range(k):
            await pg.goto(BASE); await pg.wait_for_timeout(100)
            await pg.click(f'{sel} >> nth={i}'); await pg.wait_for_timeout(120)
            if not await pg.evaluate("document.querySelector('#modal').classList.contains('open')"): probs.append(f'{sel} {i} no modal')
            await pg.keyboard.press('Escape'); await pg.wait_for_timeout(80)
    for rid in ['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16']:
        await pg.goto(BASE+'#map'); await pg.wait_for_timeout(150)
        g=pg.locator(f"g[onclick=\"go('room-{rid}')\"]").first
        await g.scroll_into_view_if_needed(); await g.click(); await pg.wait_for_timeout(120)
        if await pg.evaluate("location.hash")!='#room-'+rid: probs.append('plan click room '+rid+' -> '+await pg.evaluate("location.hash"))
    # lightbox + gallery arrows + keyboard
    await pg.goto(BASE+'#room-5'); await pg.wait_for_timeout(200)
    await pg.click('.strip img >> nth=0'); await pg.wait_for_timeout(150)
    if not await pg.evaluate("document.querySelector('#lb').classList.contains('open')"): probs.append('lightbox did not open')
    await pg.click('#lb'); await pg.wait_for_timeout(100)
    if await pg.evaluate("document.querySelector('#lb').classList.contains('open')"): probs.append('lightbox did not close')
    await pg.goto(BASE+'#work-girlfriend'); await pg.wait_for_timeout(200)
    a=await pg.evaluate("document.querySelector('#gimg').src"); await pg.click('.gnav.r'); await pg.wait_for_timeout(100)
    if a==await pg.evaluate("document.querySelector('#gimg').src"): probs.append('gallery arrow did not change photo')
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(100)
    await pg.goto(BASE+'#room-3'); await pg.wait_for_timeout(150); await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(150)
    if await pg.evaluate("location.hash")!='#room-4': probs.append('ArrowRight room nav failed')
    for t in ['inroom','ext']:
        pass
    await pg.goto(BASE+'#work-sunsets'); await pg.wait_for_timeout(150); await pg.click('.inroom'); await pg.wait_for_timeout(150)
    if await pg.evaluate("location.hash")!='#room-3': probs.append('walk-into-room link failed')
    await pg.goto(BASE+'#work-akingdon'); await pg.wait_for_timeout(150)
    await pg.click('.vtabs button:nth-child(2)'); await pg.click('.vtabs button:nth-child(1)'); await pg.wait_for_timeout(100)
    if await pg.evaluate("document.querySelectorAll('#vpane video').length")!=2: probs.append('switching back to My clips failed')
    await pg.goto(BASE+'#room-12'); await pg.wait_for_timeout(150); await pg.click('.vcap a'); await pg.wait_for_timeout(150)
    if await pg.evaluate("location.hash")!='#work-bengazarra': probs.append('room clip link failed')
    await pg.goto(BASE+'#work-akingdon'); await pg.wait_for_timeout(200)
    before = await pg.evaluate("document.querySelector('.sbody .concept').textContent")
    await pg.evaluate("setLang(LANG==='ru'?'en':'ru')"); await pg.wait_for_timeout(200)
    after = await pg.evaluate("document.querySelector('.sbody .concept').textContent")
    if before==after: probs.append('language switch did not change work text')
    if not await pg.evaluate("document.querySelector('#modal').classList.contains('open')"): probs.append('language switch closed the work')
    await pg.evaluate(f"setLang('{lang}')"); await pg.wait_for_timeout(100)
    th0=await pg.evaluate("document.documentElement.dataset.theme")
    if th0!=theme: probs.append('theme not applied: '+str(th0))
    await pg.goto(BASE+'#room-7'); await pg.wait_for_timeout(150); await pg.evaluate("scrollTo(0,400)")
    await pg.click('#themebtn'); await pg.wait_for_timeout(120)
    if not await pg.evaluate("document.querySelector('#skinmenu').classList.contains('open')"): probs.append('skin menu did not open')
    other = 'laguna' if theme!='laguna' else 'dark'
    await pg.click(f"#skinmenu button[onclick=\"setSkin('{other}')\"]"); await pg.wait_for_timeout(150)
    if await pg.evaluate("document.documentElement.dataset.theme")!=other: probs.append('skin menu did not switch')
    if await pg.evaluate("scrollY")<300: probs.append('skin switch jumped to top')
    await pg.evaluate(f"setSkin('{theme}')"); await pg.wait_for_timeout(100)
    low = await pg.evaluate(r'''() => { const lum=c=>{const m=c.match(/[\d.]+/g).map(Number);const f=v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)};return .2126*f(m[0])+.7152*f(m[1])+.0722*f(m[2])};
      const bgOf=e=>{while(e){const c=getComputedStyle(e).backgroundColor; if(c&&!c.endsWith(', 0)')&&c!=='transparent') return c; e=e.parentElement;} return getComputedStyle(document.body).backgroundColor};
      const out=[]; document.querySelectorAll('#room h2,#room .room-intro,#room .meta h4,#room .roomnav button,.bar .pill,.logo').forEach(e=>{ if(!e.offsetParent) return;
        const a=lum(getComputedStyle(e).color), b=lum(bgOf(e)); const r=(Math.max(a,b)+.05)/(Math.min(a,b)+.05); if(r<4.5) out.push(e.className+' '+r.toFixed(1)); }); return out; }''')
    for l in low: probs.append(f'{theme}: low contrast {l}')
    await pg.goto(BASE); await pg.click('.logo'); await pg.click('.bar .pill >> nth=2'); await pg.wait_for_timeout(150)
    if await pg.evaluate("location.hash")!='#map': probs.append('Map button failed')
    await pg.screenshot(path=f'/home/claude/chk_{lang}_{vw}.png')
    await b.close(); return probs
async def main():
    async with async_playwright() as p:
        engines=[('chromium',p.chromium)]
        try:
            b=await p.webkit.launch(); await b.close(); engines.append(('webkit',p.webkit))
        except Exception as e: print('webkit unavailable')
        for name,eng in engines:
            for lang,theme in [('ru','dark'),('en','dark'),('ru','light')]:
              for vw,vh in [(390,844),(1280,800)]:
                probs=await run(eng,vw,vh,lang,theme)
                print(f'== {name} {lang} {theme} {vw}px: {len(probs)} problems'); [print('  ',x) for x in probs[:40]]
asyncio.run(main())
