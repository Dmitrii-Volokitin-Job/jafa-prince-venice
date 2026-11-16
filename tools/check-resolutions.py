# Layout check at many resolutions + contrast per skin
import asyncio, re
from playwright.async_api import async_playwright
BASE='http://localhost:8765/'
SIZES=[(320,568,'iPhone SE 1'),(375,667,'iPhone SE'),(390,844,'iPhone 14'),(430,932,'iPhone Pro Max'),(768,1024,'iPad mini'),(820,1180,'iPad Air'),(1024,1366,'iPad Pro'),(1180,820,'iPad landscape'),(1366,768,'Laptop'),(1920,1080,'Desktop FHD')]
SKINS=['dark','light','laguna','terracotta','contrast']
LAYOUT=open(__import__('os').path.join(__import__('os').path.dirname(__file__),'check-site.py')).read().split('JS_LAYOUT = """')[1].split('"""')[0]
CONTRAST=r'''() => { const lum=c=>{const m=c.match(/[\d.]+/g).map(Number);const f=v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)};return .2126*f(m[0])+.7152*f(m[1])+.0722*f(m[2])};
 const bgOf=e=>{while(e){const c=getComputedStyle(e).backgroundColor; if(c&&!/, 0\)$/.test(c)&&c!=='transparent') return c; e=e.parentElement;} return getComputedStyle(document.body).backgroundColor};
 const out=[]; document.querySelectorAll('h1,h2,h3,h4,h5,p,li,.pill,.chip,.who,.yr,.kicker,.tag,.lead,.med,.roomnav button,.legend span,.facts li,.sbody .concept,.looktext,.bgtext,.inroom,.ext').forEach(e=>{
   if(!e.offsetParent||e.closest('.hero,.ph,.gal,.vtabs,.vpane')) return; const st=getComputedStyle(e); if(parseFloat(st.opacity)<1) return;
   const a=lum(st.color), b=lum(bgOf(e)); const r=(Math.max(a,b)+.05)/(Math.min(a,b)+.05); const big=parseFloat(st.fontSize)>=18.6||(parseFloat(st.fontSize)>=14&&+st.fontWeight>=700);
   if(r<(big?3:4.5)) out.push((e.className||e.tagName)+' '+r.toFixed(2)+' '+e.textContent.trim().slice(0,30)); }); return [...new Set(out)].slice(0,8); }'''
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); total=0
        ids=None
        for vw,vh,name in SIZES:
            ctx=await b.new_context(viewport={'width':vw,'height':vh}, is_mobile=vw<1000, has_touch=vw<1100)
            pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            await pg.goto(BASE+'?nogate=1'); await pg.wait_for_timeout(300)
            if ids is None: ids=await pg.evaluate("({rooms:HS.rooms.map(r=>r.id),works:HS.works.map(w=>w.id)})")
            probs=[]
            pages=['','map','thread-protest']+['room-'+r for r in ids['rooms']]+['work-'+w for w in ids['works'][::3]]
            for h in pages:
                await pg.goto(BASE+'?nogate=1#'+h); await pg.wait_for_timeout(180)
                for y in (0,600,1400):
                    if h.startswith('work-'): await pg.evaluate(f"document.querySelector('#modal').scrollTop={y}")
                    else: await pg.evaluate(f"scrollTo(0,{y})")
                    await pg.wait_for_timeout(40)
                    for x in await pg.evaluate(LAYOUT): probs.append(f'#{h}@{y}: {x}')
                # tap targets in header
                small=await pg.evaluate("[...document.querySelectorAll('.bar button, .bar .logo')].filter(e=>e.offsetParent).map(e=>e.getBoundingClientRect()).filter(r=>r.height<32||r.width<32).length")
                if small: probs.append(f'#{h}: {small} header tap targets <32px')
                hb=await pg.evaluate("(()=>{const b=document.querySelector('.bar .wrap'); return b.scrollWidth>b.clientWidth+1})()")
                if hb: probs.append(f'#{h}: header overflows')
            probs=sorted(set(probs))+errs
            total+=len(probs); print(f'== {vw}x{vh} {name}: {len(probs)} problems'); [print('   ',x) for x in probs[:12]]
            await pg.screenshot(path=f'/home/claude/res_{vw}.png'); await ctx.close()
        for sk in SKINS:
            ctx=await b.new_context(viewport={'width':390,'height':844}); pg=await ctx.new_page(); probs=[]
            for h in ['','room-10','room-17','thread-sun','work-graduation','work-loml']:
                await pg.goto(BASE+f'?nogate=1&skin={sk}#'+h); await pg.wait_for_timeout(220)
                for y in (0,500,1200):
                    if h.startswith('work-'): await pg.evaluate(f"document.querySelector('#modal').scrollTop={y}")
                    else: await pg.evaluate(f"scrollTo(0,{y})")
                    await pg.wait_for_timeout(40)
                    for x in await pg.evaluate(CONTRAST): probs.append(f'#{h}: {x}')
            probs=sorted(set(probs)); total+=len(probs); print(f'== skin {sk}: {len(probs)} contrast problems'); [print('   ',x) for x in probs[:12]]
            await ctx.close()
        print('TOTAL',total); await b.close()
asyncio.run(main())
