// Ověření klávesnice a textového přehledu. Spuštění: node tools/check_accessibility.cjs
const {createRequire}=require('module');
const requireRepo=createRequire(__filename);
const {chromium}=requireRepo('playwright');
const assert=require('node:assert/strict');
const {createServer}=require('node:http');
const {readFileSync,mkdtempSync,existsSync}=require('node:fs');
const path=require('node:path');
const os=require('node:os');
// HTTP funguje i ve spravovaném Chromiu, které blokuje file://.
const html=readFileSync(path.join(__dirname,'../index.html'));
const shots=mkdtempSync(path.join(os.tmpdir(),'jmk-accessibility-'));
const server=createServer((req,res)=>{res.setHeader('Content-Type','text/html; charset=utf-8');res.end(html);});
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));server.unref();
 const base='http://127.0.0.1:'+server.address().port;
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM||(existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined)});
 try{
 for(const mobile of [false,true]){
  const ctx=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:900},isMobile:mobile,colorScheme:mobile?'dark':'light',reducedMotion:'reduce'});
  await ctx.route(/^https?:\/\//,r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
  const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/#cas=08:00');
  const state=()=>page.evaluate(()=>({t,playing,live}));
  await page.keyboard.press('ArrowRight');assert.equal((await state()).t,29400);
  await page.keyboard.press('Shift+ArrowLeft');assert.equal((await state()).t,25800);
  await page.locator('#scrub').focus();await page.keyboard.press('ArrowRight');assert.equal((await state()).t,26400);
  await page.keyboard.press('Home');assert.equal((await state()).t,26400);
  await page.keyboard.press('Space');assert.equal((await state()).playing,true);
  await page.keyboard.press('Space');assert.equal((await state()).playing,false);
  await page.locator('#play').focus();await page.keyboard.press('Space');assert.equal((await state()).playing,true);
  await page.locator('#listB').click();assert.equal((await state()).playing,false);
  assert.equal(await page.locator('#listTitle').evaluate(e=>e===document.activeElement),true);
  assert.equal(await page.locator('#tripRows button').count(),20);
  assert.match(await page.locator('#listStatus').innerText(),/Čas 07:2/);
  await page.locator('#listNext').click();assert.match(await page.locator('#listStatus').innerText(),/zobrazeny 21–40/);
  const original=(await state()).t;
  await page.locator('#tripQuery').fill('Hlavni nadrazi');assert.ok(await page.locator('#tripRows button').count()>0);
  await page.keyboard.press('ArrowLeft');await page.keyboard.press('Space');assert.equal((await state()).t,original);assert.equal((await state()).playing,false);
  await page.locator('#tripQuery').fill('neexistujici-zastavka-xyz');assert.equal(await page.locator('#tripRows button').count(),0);assert.match(await page.locator('#listStatus').innerText(),/Žádné spoje/);
  await page.locator('#tripQuery').fill('');
  const name=await page.locator('#tripRows button').first().innerText();
  const selected=await page.locator('#tripRows button').first().getAttribute('data-trip');
  await page.locator('#tripRows button').first().focus();await page.keyboard.press('Enter');
  assert.equal(await page.locator('#veh').isVisible(),true);assert.equal(await page.locator('#tripList').isVisible(),false);
  assert.ok(await page.locator('#vStops li').count()>0);assert.ok(name.includes(await page.locator('#vSub').innerText().then(t=>t.replace(/^Směr /,'').split(' · ')[0])));
  await page.keyboard.press('Escape');assert.equal(await page.locator('#tripList').isVisible(),true);
  assert.equal(await page.evaluate(()=>document.activeElement.dataset.trip),selected);
  await page.locator('#listTitle').focus();
  await page.keyboard.press('Escape');assert.equal(await page.locator('#listB').evaluate(e=>e===document.activeElement),true);
  await page.locator('#recB').click();await page.locator('#listB').click();assert.equal(await page.locator('#rec').isVisible(),false);
  await page.keyboard.press('ArrowRight');assert.equal((await state()).t,original+600);
  await page.evaluate(()=>{t=86340;playing=false;});await page.keyboard.press('ArrowRight');assert.equal((await state()).t,86340);
  await page.evaluate(()=>{t=0;});await page.keyboard.press('ArrowLeft');assert.equal((await state()).t,0);
  await page.evaluate(()=>{t=28800;on.fill(0);});await page.waitForTimeout(200);assert.match(await page.locator('#listStatus').innerText(),/Žádné spoje/);
  await page.evaluate(()=>{on.fill(1);});await page.waitForTimeout(200);
  await page.screenshot({path:path.join(shots,`list-${mobile?'mobile':'desktop'}.png`)});
  assert.deepEqual(errors,[]);console.log(`${mobile?'mobil / tmavý':'desktop'}: klávesy, hranice dne, nativní tlačítka, hledání, stránkování, detail, návrat, filtry: OK`);
  await ctx.close();
 }
 }finally{await browser.close();server.close();}
 console.log('Snímky: '+shots);
})().catch(e=>{console.error(e);process.exit(1)});
