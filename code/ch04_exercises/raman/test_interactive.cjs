'use strict';
// Built-in Node assertions for the exact data used by the browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../../..');
const lab = require(path.join(root, 'assets/js/ch04-lab.js'));
const context = {window: {}};
vm.runInNewContext(fs.readFileSync(path.join(root, 'assets/js/ch04-results.js'), 'utf8'), context);
const data = context.window.IAC_CH04_DATA;
for (const strategy of ['row_random', 'specimen_group']) {
  assert.equal(data.folds[strategy].length, 72);
  for (let fold = 1; fold <= 4; fold++) {
    const s = lab.splitSummary(data.folds[strategy], fold);
    assert.equal(s.train + s.valid, 216);
    assert.equal(s.valid, 54);
    if (strategy === 'specimen_group') assert.equal(s.overlap, 0);
    else assert(s.overlap > 0);
  }
}
for (const seed of data.extensions.seeds) {
  for (const model of ['Dummy', 'raw_SVC', 'arPLS_L2_SVC']) {
    const rows = data.panel_predictions.filter(r => r.seed === seed && r.model === model && r.instrument === 'B');
    assert.equal(rows.length, 18);
    const m = lab.matrixFromRows(rows, 3);
    assert.equal(m.flat().reduce((a, b) => a + b, 0), 18);
  }
}
console.log('PASS: 8 split views and 15 panel confusion matrices match exported data.');
