// Requires Playwright + Edge. Run against the local static server on port 8765.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');

(async () => {
  const browser = await chromium.launch({channel:'msedge', headless:true});
  try {
    const context = await browser.newContext({viewport:{width:390,height:844}, reducedMotion:'reduce'});
    // Isolate the UI from LINE, Maps and other external services; no external writes.
    await context.route('**/*', route => new URL(route.request().url()).hostname === '127.0.0.1' ? route.continue() : route.abort());
    await context.addInitScript(() => {
      window.prologueGpsCalls = 0;
      navigator.geolocation.getCurrentPosition = () => { window.prologueGpsCalls++; };
    });
    const page = await context.newPage();
    const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    const base=process.env.QUEST_TEST_URL || 'http://127.0.0.1:8765/';
    const modal=page.locator('#questPrologueModal');
    const pick=async ids=>{for(const id of ids) await modal.locator(`[data-prologue-id="${id}"]`).click();};
    const open=async()=>{await page.locator('#questTrialBtn').click(); await modal.waitFor({state:'visible'});};
    const saved=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('wanchun_quest_prologue_v1')));
    const screenshotDir=process.env.QUEST_SCREENSHOT_DIR;
    if(screenshotDir)fs.mkdirSync(screenshotDir,{recursive:true});
    await page.goto(`${base}?page=quest`);
    await open();
    assert(await modal.locator('#questPrologueCheck').isDisabled());
    assert.equal(await modal.locator('#questPrologueReveal').innerHTML(),'');
    assert(!/店頭媽|聖筊擺飾|金色平安符|第二市場/.test(await modal.innerText()));
    if(screenshotDir)await page.screenshot({path:path.join(screenshotDir,'prologue-start.png')});
    await pick(['C','A','B']);
    await modal.locator('#questPrologueCheck').click();
    assert((await modal.locator('#questPrologueStatus').innerText()).includes('還差一點'));
    assert(await modal.locator('#questPrologueReveal').isHidden());
    for(let i=0;i<3;i++)await modal.locator('#questPrologueUndo').click();
    await modal.getByRole('button',{name:'一點提示'}).click();
    await pick(['B']);
    await page.keyboard.press('Escape');
    assert(await page.locator('#questGameModal').isVisible());
    await open();
    assert.deepEqual((await saved()).order,['B']);
    await page.reload();
    await open();
    assert((await modal.locator('[data-prologue-slot="0"]').innerText()).includes('殘頁乙'));
    assert((await modal.locator('#questPrologueStatus').innerText()).includes('空間改變'));
    await pick(['A','C']);
    await modal.locator('#questPrologueCheck').click();
    assert(await modal.locator('#questPrologueReveal').isVisible());
    assert((await modal.innerText()).includes('店頭媽'));
    assert.equal(await modal.locator('.lb-sheet').evaluate(el=>el.scrollTop),0,'Reveal starts at the title, not midway down the sheet');
    assert.equal((await saved()).completed,true);
    // Route data is intentionally lazy in the app; initialize for guard checks.
    await page.evaluate(()=>rebuildDynamicRoutes(24.1432,120.6806));
    assert.deepEqual(await page.evaluate(()=>({paid:localStorage.getItem('wanchun_quest_active'),trial:localStorage.getItem('wanchun_quest_trial'),stamps:getUserFootprints(),frontier:getQuestFrontier(),map:getCurrentQuestMapIndex()})),{paid:null,trial:null,stamps:[],frontier:0,map:-1});
    const routeHtml=await page.evaluate(()=>renderMysteryCheckpoints());
    assert(routeHtml.includes('序章・她曾有另一個名字'));
    assert(!/萬春山門|第二市場|聖筊擺飾|金色平安符/.test(routeHtml));
    if(screenshotDir)await page.screenshot({path:path.join(screenshotDir,'prologue-reveal.png')});
    await page.reload();
    await open();
    assert(await modal.locator('#questPrologueReveal').isVisible());
    await modal.getByRole('button',{name:'再拼一次序章'}).click();
    assert.equal((await saved()).completed,true);
    assert.equal((await saved()).solved,false);
    assert.equal(await modal.locator('#questPrologueReveal').innerHTML(),'');
    // Keyboard focus stays within the active sheet, Escape returns to entry.
    await modal.locator('.lb-sheet-close').focus();
    await page.keyboard.press('Shift+Tab');
    assert.equal(await page.evaluate(()=>document.activeElement.textContent),'一點提示');
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('aria-label')),'暫別序章，保留進度');
    for(const width of [320,390,768]) {
      await page.setViewportSize({width,height:844});
      assert(await modal.locator('.lb-sheet').evaluate(el=>el.scrollWidth<=el.clientWidth));
    }
    await page.keyboard.press('Escape');
    // Corrupt save recovers without changing the existing paid journey.
    await page.evaluate(()=>{
      localStorage.setItem('wanchun_quest_prologue_v1','{invalid');
      localStorage.setItem('wanchun_quest_active','true');
      localStorage.setItem('temple_footprints_v3',JSON.stringify(['wc_1','wc_2']));
    });
    await page.goto(`${base}?page=routedetail&route=wanchun`);
    await page.locator('.mystery-history summary').click();
    await page.locator('.mystery-history').getByRole('button',{name:'拆開三張殘頁・免費試玩序章 →'}).click();
    assert.equal((await modal.locator('[data-prologue-slot="0"]').innerText()),'第一段');
    await pick(['B','A','C']);
    await modal.locator('#questPrologueCheck').click();
    assert.deepEqual(await page.evaluate(()=>({paid:localStorage.getItem('wanchun_quest_active'),stamps:getUserFootprints(),frontier:getQuestFrontier()})),{paid:'true',stamps:['wc_1','wc_2'],frontier:2});
    // Quota/storage failure: the puzzle is playable and warns about persistence.
    await modal.getByRole('button',{name:'再拼一次序章'}).click();
    await page.evaluate(()=>{Storage.prototype.setItem=function(){throw new Error('quota');};});
    await pick(['B','A','C']);
    await modal.locator('#questPrologueCheck').click();
    assert(await modal.locator('#questPrologueReveal').isVisible());
    assert(await modal.locator('#questPrologueStorageNote').isVisible());
    assert.deepEqual(errors,[]);
    console.log('PASS: entry, spoiler guards, wrong answer, hint, undo, resume/reload, solve, replay, paid isolation, legacy progress, corrupt save, quota fallback, keyboard, 320/390/768px layouts; no runtime errors.');
    await context.close();
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
