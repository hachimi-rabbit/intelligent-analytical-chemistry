'use strict';
// Optional integration test: npm install playwright && npx playwright install chromium
// Run from any directory. CHROMIUM_EXECUTABLE and G04_SCREENSHOT_DIR are optional.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const {pathToFileURL} = require('node:url');
const root = path.resolve(__dirname, '../../..');
const data = require(path.join(root, 'assets/js/ch04-results.js'));
const lab = require(path.join(root, 'assets/js/ch04-lab.js'));
(async () => {
  const browser = await chromium.launch({headless: true,
    ...(process.env.CHROMIUM_EXECUTABLE ? {executablePath: process.env.CHROMIUM_EXECUTABLE} : {}),
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']});
  try {
    const page = await browser.newPage({viewport: {width: 1360, height: 1000}});
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(pathToFileURL(path.join(root, 'assets/interactive/ch04.html')).href);
    await page.waitForSelector('.g04-specimen');
    assert.equal(await page.locator('.g04-specimen').count(), 72);
    const select = (k, v) => page.locator('[data-control="'+k+'"]').selectOption(String(v));
    for (const strategy of ['row_random', 'specimen_group']) {
      await select('strategy', strategy);
      for (let fold = 1; fold <= 4; fold++) {
        await select('fold', fold);
        const s = lab.splitSummary(data.folds[strategy], fold);
        assert.equal(await page.locator('.g04-leak').count(), s.overlap);
        assert((await page.locator('[data-view="summary"]').innerText()).includes('共享'+s.overlap+'个'));
        for (const model of ['Dummy', '1NN', 'PCA_LR', 'RBF_SVC']) {
          await select('model', model);
          assert.equal(await page.locator('[data-view="cv"] strong').first().innerText(), data.cv[strategy][model].sample.macro_f1.toFixed(4));
        }
      }
    }
    for (const instrument of ['A', 'B']) {
      await select('instrument', instrument);
      assert.equal(await page.locator('[data-view="holdout"] strong').innerText(), data.holdout[instrument].sample.macro_f1.toFixed(4));
    }
    for (const seed of data.extensions.seeds) {
      await select('seed', seed);
      for (const model of ['raw_SVC', 'arPLS_L2_SVC', 'Dummy']) {
        await select('pipeline', model);
        const cells = await page.locator('[data-view="panel"] td').allTextContents();
        const expected = lab.matrixFromRows(data.panel_predictions.filter(r => r.seed === seed && r.model === model && r.instrument === 'B'), 3);
        assert.deepEqual(cells.map(Number), expected.flat());
      }
    }
    assert.equal(await page.locator('[data-view="answer"]').isVisible(), false);
    await page.locator('[data-control="answer"]').click();
    assert.equal(await page.locator('[data-view="answer"]').isVisible(), true);
    await page.locator('[data-control="answer"]').click();
    assert.equal(await page.locator('[data-view="answer"]').isVisible(), false);
    for (const width of [1360, 390, 320]) {
      await page.setViewportSize({width, height: 1000});
      await select('strategy', 'row_random'); await select('model', 'RBF_SVC');
      const geometry = await page.evaluate(() => ({body: document.documentElement.scrollWidth, viewport: innerWidth}));
      assert(geometry.body <= geometry.viewport, JSON.stringify(geometry));
      if (process.env.G04_SCREENSHOT_DIR) {
        fs.mkdirSync(process.env.G04_SCREENSHOT_DIR, {recursive: true});
        await page.screenshot({path: path.join(process.env.G04_SCREENSHOT_DIR, 'interactive-'+width+'.png'), fullPage: true});
      }
    }
    assert.deepEqual(errors, []);
    console.log('PASS: 32 CV combinations, A/B, 15 panel matrices, answer toggle, 3 responsive widths; no JavaScript errors.');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
