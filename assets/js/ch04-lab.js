/* G04: inspect actual precomputed Python results. No browser model fitting. */
(function (root) {
  'use strict';
  function splitSummary(records, fold) {
    var train = 0, valid = 0, overlap = 0;
    records.forEach(function (r) {
      var n = r.folds.filter(function (f) { return f === fold; }).length;
      valid += n; train += r.folds.length - n;
      if (n > 0 && n < r.folds.length) overlap += 1;
    });
    return { train: train, valid: valid, overlap: overlap };
  }
  function matrixFromRows(rows, size) {
    var m = Array.from({ length: size }, function () { return Array(size).fill(0); });
    rows.forEach(function (r) { m[r.true_class][r.predicted_class] += 1; });
    return m;
  }
  function matrixHTML(matrix, classes) {
    var html = '<table class="g04-matrix"><caption>混淆矩阵，行为真实类别，列为预测类别，单位为标本</caption><thead><tr><th scope="col">真实 / 预测</th>';
    classes.forEach(function (c) { html += '<th scope="col">' + c + '</th>'; });
    html += '</tr></thead><tbody>';
    matrix.forEach(function (row, i) {
      html += '<tr><th scope="row">' + classes[i] + '</th>';
      row.forEach(function (v, j) { html += '<td class="' + (i === j ? 'g04-diagonal' : '') + '">' + v + '</td>'; });
      html += '</tr>';
    });
    return html + '</tbody></table>';
  }
  function bar(label, value) {
    return '<div class="g04-bar"><span>' + label + '</span><div><i style="width:' + (value*100).toFixed(2) + '%"></i></div><strong>' + value.toFixed(4) + '</strong></div>';
  }
  function render(el, data) {
    if (el.dataset.g04Mounted) return;
    el.dataset.g04Mounted = 'true';
    el.innerHTML = '<header><p class="g04-eyebrow">第4章 · 拉曼教学实验</p><h3>模型学到的是矿物，还是标本身份？</h3><p>查看真实计算输出，检查划分边界，再比较换仪器与预处理后的变化。</p><p class="g04-status">全部为教学模拟。模型结果预先计算，页面不重新训练，也不上传数据。</p></header>'
      + '<div class="g04-controls"><label>划分方式<select data-control="strategy"><option value="row_random">逐谱随机划分（反例）</option><option value="specimen_group">按物理标本分组</option></select></label><label>查看验证折<select data-control="fold"><option>1</option><option>2</option><option>3</option><option>4</option></select></label><label>模型<select data-control="model"><option value="RBF_SVC">RBF-SVC</option><option value="PCA_LR">PCA + 逻辑回归</option><option value="1NN">1NN</option><option value="Dummy">多数类</option></select></label></div>'
      + '<p class="g04-summary" data-view="summary" role="status" aria-live="polite"></p><p class="g04-legend">每格为一个标本，三段代表三次扫描。灰色“训”为训练，蓝色“验”为验证；红框表示同一标本跨越两侧。</p><div class="g04-grid" data-view="grid"></div>'
      + '<div class="g04-results" data-view="cv"></div>'
      + '<section class="g04-section"><h4>冻结模型后，同一批未见标本换仪器</h4><p>仅展示按开发分组结果选出的RBF-SVC。18个标本在A、B上配对测量，仍是18个独立对象。</p><label>测试仪器<select data-control="instrument"><option value="A">A：同仪器新标本</option><option value="B">B：另一仪器，同批新标本</option></select></label><div data-view="holdout"></div></section>'
      + '<section class="g04-section"><h4>五个固定种子的预处理对照</h4><p>处理流程为逐谱arPLS基线扣除与L2归一化，再拟合SVC。没有波数轴校准；每个种子的全部候选均报告。</p><div class="g04-controls"><label>模拟种子<select data-control="seed">' + data.extensions.seeds.map(function(s){return '<option>'+s+'</option>';}).join('') + '</select></label><label>处理流程<select data-control="pipeline"><option value="raw_SVC">原始变量标准化 + SVC</option><option value="arPLS_L2_SVC">arPLS + L2归一化 + SVC</option><option value="Dummy">多数类基线</option></select></label></div><div data-view="panel"></div><p class="g04-status">这些高分仅属于简化三分类模拟，不是实测矿物性能，也不证明任意仪器都能迁移。</p></section>'
      + '<section class="g04-section"><h4>随机标签也能得到高分吗？</h4><p>199次标本级标签置换，1NN逐谱随机宏F1均值 ' + data.extensions.null_summary.row_random.mean.toFixed(4) + '；按标本分组均值 ' + data.extensions.null_summary.specimen_group.mean.toFixed(4) + '。随机标签不含矿物类别信息，重复谱仍可暴露身份。</p><button type="button" data-control="answer" aria-expanded="false">查看判断题答案</button><p data-view="answer" hidden>判断题：把同一标本的三次折外预测投票，能否修复逐谱随机划分？不能。验证扫描的同标本信息已经进入训练，事后聚合不改变训练边界。</p></section>';
    function view(name) { return el.querySelector('[data-view="'+name+'"]'); }
    function value(name) { return el.querySelector('[data-control="'+name+'"]').value; }
    function updateCV() {
      var strategy=value('strategy'), fold=Number(value('fold')), model=value('model');
      var records=data.folds[strategy], counts=splitSummary(records,fold);
      view('summary').textContent='第'+fold+'折：训练'+counts.train+'条，验证'+counts.valid+'条；两侧共享'+counts.overlap+'个物理标本。';
      view('grid').innerHTML=records.map(function(r){
        var n=r.folds.filter(function(f){return f===fold;}).length;
        return '<div class="g04-specimen '+(n>0&&n<3?'g04-leak':'')+'"><span>'+r.id+'</span><div>'+r.folds.map(function(f){return '<b class="'+(f===fold?'g04-valid':'g04-train')+'">'+(f===fold?'验':'训')+'</b>';}).join('')+'</div></div>';
      }).join('');
      var selected=data.cv[strategy][model].sample;
      view('cv').innerHTML='<h4>'+model+'：全部4折的折外标本结果</h4>'
        +bar('宏平均F1',selected.macro_f1)+bar('平衡准确率',selected.balanced_accuracy)
        +matrixHTML(selected.confusion_matrix,data.classes)
        +'<p>这里汇总72个开发标本，不是上方单一验证折的分数。'+(strategy==='row_random'?'逐谱随机结果只作为泄漏反例，不参与选模。':'本列用于候选选择，最终性能仍看留出集。')+'</p>';
    }
    function updateHoldout() {
      var instrument=value('instrument'), m=data.holdout[instrument].sample;
      view('holdout').innerHTML=bar('仪器'+instrument+' 宏F1',m.macro_f1)+matrixHTML(m.confusion_matrix,data.classes);
    }
    function updatePanel() {
      var seed=Number(value('seed')), model=value('pipeline');
      var rows=data.panel.filter(function(r){return r.seed===seed&&r.model===model;});
      var label={group_cv:'开发分组宏F1',holdout_A:'A留出宏F1',holdout_B:'B留出宏F1'};
      var selected=data.extensions.selection.filter(function(r){return r.seed===seed;})[0].selected_model;
      view('panel').innerHTML='<p>种子'+seed+'，开发集选出的流程：<strong>'+selected+'</strong>。当前查看：'+model+'。</p>'+rows.map(function(r){return bar(label[r.evaluation],r.macro_f1);}).join('')
        +matrixHTML(matrixFromRows(data.panel_predictions.filter(function(r){return r.seed===seed&&r.model===model&&r.instrument==='B';}),3),data.classes);
    }
    ['strategy','fold','model'].forEach(function(k){el.querySelector('[data-control="'+k+'"]').addEventListener('change',updateCV);});
    el.querySelector('[data-control="instrument"]').addEventListener('change',updateHoldout);
    ['seed','pipeline'].forEach(function(k){el.querySelector('[data-control="'+k+'"]').addEventListener('change',updatePanel);});
    el.querySelector('[data-control="answer"]').addEventListener('click',function(){var a=view('answer');a.hidden=!a.hidden;this.textContent=a.hidden?'查看判断题答案':'收起答案';this.setAttribute('aria-expanded',String(!a.hidden));});
    updateCV();updateHoldout();updatePanel();
  }
  function mount() {
    if (!root.IAC_CH04_DATA) return;
    root.document.querySelectorAll('.ch04-lab').forEach(function(el){render(el,root.IAC_CH04_DATA);});
  }
  if (typeof module==='object' && module.exports) { module.exports={splitSummary:splitSummary,matrixFromRows:matrixFromRows,render:render}; return; }
  root.$docsify=root.$docsify||{};
  root.$docsify.plugins=(root.$docsify.plugins||[]).concat(function(hook){hook.doneEach(mount);});
  root.document.addEventListener('DOMContentLoaded',mount);
  if (root.document.readyState!=='loading') mount();
})(typeof window!=='undefined'?window:this);
