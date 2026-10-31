'use strict';
(() => {
 const d=window.RRUFF_FULL,$=id=>document.getElementById(id);
 if(!d){$('coverage').textContent='数据未加载。请完整解压项目并保留相邻文件。';return;}
 const labels={Dummy:'多数类基线',Cosine_1NN:'余弦近邻',PCA8_LR:'PCA＋逻辑回归',RBF_SVC:'SVM'};
 const s=d.summary;
 $('coverage').textContent=`来源共有${s.source_spectra.toLocaleString()}条谱、${s.source_specimens.toLocaleString()}个标本、${s.source_classes.toLocaleString()}类矿物。审查后，${s.usable_spectra.toLocaleString()}条谱用于最终训练，覆盖${s.usable_classes.toLocaleString()}类。`;
 $('evaluation').textContent=`${s.evaluated_spectra.toLocaleString()}条谱、${s.evaluated_groups.toLocaleString()}个验证组、${s.evaluated_classes}个类别接受折外验证。另有${s.training_only_classes.toLocaleString()}个单组类别仅参与训练。`;
 const counts=new Map();for(const r of d.spectra){if(!counts.has(r.mineral))counts.set(r.mineral,[]);counts.get(r.mineral).push(r);}
 function option(select,value,label){const o=document.createElement('option');o.value=value;o.textContent=label;select.append(o);}
 for(const c of d.classes)option($('mineral'),c,`${c}（${counts.get(c).length}条谱）`);
 for(const n of Object.keys(s.metrics)){
  option($('model'),n,labels[n]);const row=$('metrics').insertRow();const m=s.metrics[n].group;
  [labels[n],(100*m.accuracy).toFixed(1)+'%',(m.macro_f1<0.001?m.macro_f1.toFixed(6):m.macro_f1.toFixed(4)),m.balanced_accuracy.toFixed(4)].forEach(v=>row.insertCell().textContent=v);
 }
 $('model').value='Cosine_1NN';$('mineral').value='Quartz';
 const NS='http://www.w3.org/2000/svg';
 function elem(t,a,v){const e=document.createElementNS(NS,t);Object.entries(a).forEach(([k,x])=>e.setAttribute(k,x));if(v!==undefined)e.textContent=v;return e;}
 function draw(r){const svg=$('plot');svg.replaceChildren();const lo=Math.min(0,...r.y),hi=Math.max(...r.y)*1.08;
  const x=v=>85+(v-304)/(852-304)*885,y=v=>310-(v-lo)/(hi-lo)*280;
  for(const v of [304,400,500,600,700,800,852])svg.append(elem('line',{x1:x(v),x2:x(v),y1:25,y2:310,stroke:'#e4ebef'}),elem('text',{x:x(v),y:342,'text-anchor':'middle'},v));
  for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4;svg.append(elem('text',{x:75,y:y(v)+6,'text-anchor':'end'},v.toFixed(3)));}
  svg.append(elem('polyline',{points:d.axis.map((v,i)=>`${x(v)},${y(r.y[i])}`).join(' '),fill:'none',stroke:'#176c96','stroke-width':2}),elem('text',{x:530,y:382,'text-anchor':'middle'},'拉曼位移 / cm⁻¹'),elem('text',{transform:'translate(21 175) rotate(-90)','text-anchor':'middle'},'L2归一化强度'));
 }
 function update(){const r=counts.get($('mineral').value).find(v=>v.id===$('spectrum').value);const model=$('model').value;
  $('record').textContent=`参考矿物：${r.mineral}；标本：${r.specimen}；验证组：${r.group}；激光波长：${r.laser} nm。`;
  $('prediction').textContent=r.fold<0?'本类别只有一个验证组，本谱只参与训练，没有独立的同类新标本验证预测。':`第${r.fold+1}折完整留出本组。${labels[model]}预测：${d.classes[r.predictions[model]]}；${d.classes[r.predictions[model]]===r.mineral?'与参考标签一致':'与参考标签不一致'}。`;
  draw(r);
 }
 function choose(){ $('spectrum').replaceChildren();for(const r of counts.get($('mineral').value))option($('spectrum'),r.id,`${r.specimen} · ${r.laser} nm · 谱${r.id}`);update();}
 $('mineral').addEventListener('change',choose);$('spectrum').addEventListener('change',update);$('model').addEventListener('change',update);choose();
})();
