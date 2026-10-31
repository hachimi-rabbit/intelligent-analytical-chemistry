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
    var html = '<table class="g04-matrix"><caption>混淆矩阵：行为真实类别，列为预测类别，单位为标本</caption><thead><tr><th scope="col">真实 / 预测</th>';
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
    el.innerHTML = '<header><p class="g04-eyebrow">第4章 · 拉曼模拟实验</p><h3>模型学到的是矿物类别，还是标本身份？</h3><p>本模块使用程序生成的模拟数据：90个标本，每台仪器对每个标本扫描3次。切换划分方式，可检查同一标本是否同时进入训练集与验证集；后两部分比较更换仪器和预处理对性能的影响。</p><p class="g04-status">全部为教学模拟数据。结果均预先计算，页面不重新训练模型，也不上传数据。</p></header>'
      + '<div class="g04-controls"><label>划分方式<select data-control="strategy"><option value="row_random">逐谱随机划分（反例）</option><option value="specimen_group">按物理标本分组</option></select></label><label>验证折<select data-control="fold"><option>1</option><option>2</option><option>3</option><option>4</option></select></label><label>模型<select data-control="model"><option value="RBF_SVC">RBF-SVC</option><option value="PCA_LR">PCA + 逻辑回归</option><option value="1NN">1NN（最近邻）</option><option value="Dummy">多数类基线</option></select></label></div>'
      + '<p class="g04-summary" data-view="summary" role="status" aria-live="polite"></p><p class="g04-legend">每格代表一个标本，三段对应其三条光谱。灰色“训”表示训练集，蓝色“验”表示验证集；红框表示该标本同时出现在两侧。</p><div class="g04-grid" data-view="grid"></div>'
      + '<div class="g04-results" data-view="cv"></div>'
      + '<section class="g04-section"><h4>更换仪器后的性能变化</h4><p>依据开发集的分组验证结果选定RBF-SVC并固定参数，随后在18个未参与开发的标本上测试。这18个标本分别在仪器A和B上测量，构成配对数据，独立对象数仍为18。</p><label>测试仪器<select data-control="instrument"><option value="A">A：与训练相同</option><option value="B">B：另一台仪器</option></select></label><div data-view="holdout"></div></section>'
      + '<section class="g04-section"><h4>五个随机种子下的预处理对比</h4><p>比较两种处理流程：原始变量标准化后直接拟合SVM，以及逐谱arPLS基线扣除与L2归一化后再拟合SVM。随机种子决定模拟数据的生成，取5个种子以检验结论的稳定性；各种子下的全部候选均予报告。未进行波数轴校准。</p><div class="g04-controls"><label>模拟种子<select data-control="seed">' + data.extensions.seeds.map(function(s){return '<option>'+s+'</option>';}).join('') + '</select></label><label>处理流程<select data-control="pipeline"><option value="raw_SVC">原始变量 + SVM</option><option value="arPLS_L2_SVC">arPLS + L2 + SVM</option><option value="Dummy">多数类基线</option></select></label></div><div data-view="panel"></div><p class="g04-status">以上结果仅适用于简化的三分类模拟，不代表实测矿物的性能，也不证明模型可迁移至任意仪器。表中为仪器B上的混淆矩阵。</p></section>'
      + '<section class="g04-section"><h4>随机标签能否得到高分？</h4><p>将标本的类别标签随机置换199次，此时标签与光谱不再相关，宏平均F1应接近随机水平（三分类约0.33）。然而在逐谱随机划分下，1NN的平均宏F1仍达 ' + data.extensions.null_summary.row_random.mean.toFixed(4) + '；按标本分组时为 ' + data.extensions.null_summary.specimen_group.mean.toFixed(4) + '。这说明逐谱随机划分下的高分来自同一标本重复光谱所泄露的身份信息，而非模型学到了类别特征。</p><button type="button" data-control="answer" aria-expanded="false">查看判断题答案</button><p data-view="answer" hidden>判断题：在逐谱随机划分后，将同一标本三条光谱的折外预测投票汇总，能否消除泄漏？不能。验证光谱所属标本的信息已进入训练集，事后汇总不会改变训练与验证的划分边界。</p></section>';
    function view(name) { return el.querySelector('[data-view="'+name+'"]'); }
    function value(name) { return el.querySelector('[data-control="'+name+'"]').value; }
    function updateCV() {
      var strategy=value('strategy'), fold=Number(value('fold')), model=value('model');
      var records=data.folds[strategy], counts=splitSummary(records,fold);
      view('summary').textContent='第'+fold+'折：训练集'+counts.train+'条光谱，验证集'+counts.valid+'条；两侧共享'+counts.overlap+'个标本'+(counts.overlap?'，存在标本层面的数据泄漏。':'，不存在标本层面的数据泄漏。');
      view('grid').innerHTML=records.map(function(r){
        var n=r.folds.filter(function(f){return f===fold;}).length;
        return '<div class="g04-specimen '+(n>0&&n<3?'g04-leak':'')+'"><span>'+r.id+'</span><div>'+r.folds.map(function(f){return '<b class="'+(f===fold?'g04-valid':'g04-train')+'">'+(f===fold?'验':'训')+'</b>';}).join('')+'</div></div>';
      }).join('');
      var selected=data.cv[strategy][model].sample;
      view('cv').innerHTML='<h4>'+model+'：4折汇总的折外结果</h4>'
        +bar('宏平均F1',selected.macro_f1)+bar('平衡准确率',selected.balanced_accuracy)
        +matrixHTML(selected.confusion_matrix,data.classes)
        +'<p>此处汇总72个开发标本在4折中的折外预测，并非上方单一折的得分。'+(strategy==='row_random'?'逐谱随机划分的结果因泄漏而偏高，仅作反例，不用于模型选择。':'按标本分组的结果用于模型选择，最终性能以独立留出集为准。')+'</p>';
    }
    function updateHoldout() {
      var instrument=value('instrument'), m=data.holdout[instrument].sample;
      view('holdout').innerHTML=bar('仪器'+instrument+' 宏F1',m.macro_f1)+matrixHTML(m.confusion_matrix,data.classes);
    }
    function updatePanel() {
      var seed=Number(value('seed')), model=value('pipeline');
      var rows=data.panel.filter(function(r){return r.seed===seed&&r.model===model;});
      var label={group_cv:'开发集分组验证宏F1',holdout_A:'仪器A留出集宏F1',holdout_B:'仪器B留出集宏F1'};
      var selected=data.extensions.selection.filter(function(r){return r.seed===seed;})[0].selected_model;
      view('panel').innerHTML='<p>种子'+seed+'：开发集选出的流程为 <strong>'+selected+'</strong>；当前查看 '+model+'。</p>'+rows.map(function(r){return bar(label[r.evaluation],r.macro_f1);}).join('')
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
