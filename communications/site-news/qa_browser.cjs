/* Dev-only browser QA. Usage: NODE_PATH=... CHROMIUM_PATH=... node qa_browser.cjs BUILD OUTPUT */
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const root = path.resolve(process.argv[2]), out = path.resolve(process.argv[3]);
fs.mkdirSync(out, {recursive:true});
const server = http.createServer((req,res)=>{
  let p = path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
  if (!p.startsWith(root+path.sep)) {res.writeHead(404); return res.end();}
  if (fs.existsSync(p) && fs.statSync(p).isDirectory()) p=path.join(p,'index.html');
  if (!fs.existsSync(p)) {res.writeHead(404);return res.end();}
  res.setHeader('Content-Type',({'.html':'text/html; charset=utf-8','.css':'text/css','.svg':'image/svg+xml','.png':'image/png','.xml':'application/xml'})[path.extname(p)]||'application/octet-stream');
  res.end(fs.readFileSync(p));
});
(async()=>{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const origin='http://127.0.0.1:'+server.address().port;
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--use-gl=angle','--use-angle=swiftshader','--in-process-gpu']});
  const results=[];
  try {
    for(const width of [320,390,768,1440,1920]) {
      const page=await browser.newPage({viewport:{width,height:width<650?844:1000},isMobile:width<650,hasTouch:width<650});
      const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(r.status()+' '+r.url())});
      for(const route of ['/news/','/news/digital-engineer/']) {
        await page.goto(origin+route);await page.evaluate(()=>document.fonts.ready);
        const layout=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,h1:document.querySelectorAll('h1').length,
          images:[...document.images].map(x=>({loaded:x.complete&&x.naturalWidth>0,current:x.currentSrc,width:x.getBoundingClientRect().width})),
          nav:[...document.querySelectorAll('header a')].map(x=>({label:x.textContent,height:x.getBoundingClientRect().height})),
          font:getComputedStyle(document.body).fontSize}));
        assert.ok(layout.scroll<=width,JSON.stringify({width,route,layout}));assert.equal(layout.h1,1);
        assert.ok(layout.images.every(x=>x.loaded));assert.ok(layout.images[0].current.endsWith(width<=650?'cover-mobile.svg':'cover.svg'));
        if([390,1440].includes(width)) await page.screenshot({path:path.join(out,`${width}-${route.includes('digital')?'article':'listing'}.png`),fullPage:true});
        results.push({width,route,...layout});
      }
      await page.getByRole('link',{name:'← Все материалы',exact:true}).click();
      assert.match(page.url(),/\/news\/(index.html)?$/);
      await page.getByRole('link',{name:'Читать материал →',exact:true}).click();
      assert.match(page.url(),/digital-engineer\/(index.html)?$/);
      await page.goto(origin+'/news/');await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(()=>document.activeElement.textContent),'К содержанию');
      await page.keyboard.press('Enter');assert.equal(new URL(page.url()).hash,'#main');
      assert.deepEqual(errors,[]);
      await page.close();
    }
    // SVG text stays inside its viewBox (desktop and mobile).
    const p=await browser.newPage();
    for(const name of ['cover.svg','cover-mobile.svg']){
      await p.goto(origin+'/news/assets/'+name);
      const bounds=await p.evaluate(()=>{const vb=document.querySelector('svg').viewBox.baseVal;return [...document.querySelectorAll('text')].map(t=>{const b=t.getBBox();return {text:t.textContent,inside:b.x>=0&&b.y>=0&&b.x+b.width<=vb.width&&b.y+b.height<=vb.height}})});
      assert.ok(bounds.every(x=>x.inside),JSON.stringify(bounds));
    }
    fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify({browser:await browser.version(),results,navigation:'PASS',keyboard:'PASS',svgBounds:'PASS',errors:[]},null,2)+'\n');
    console.log('BROWSER_QA_PASS',results.length,'layouts; navigation, keyboard, images, SVG bounds');
  } finally {await browser.close();server.close()}
})().catch(e=>{console.error(e);server.close();process.exitCode=1});
