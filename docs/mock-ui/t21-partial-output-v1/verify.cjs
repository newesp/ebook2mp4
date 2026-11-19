// Minimal DOM substitute: verifies mock behavior, not browser layout or native app.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync(__dirname + '/index.html', 'utf8');
const ids = [...html.matchAll(/id="([^"]+)"/g)].map(m => m[1]);
assert.equal(ids.length, new Set(ids).size, 'unique element IDs');
const elements = Object.fromEntries(ids.map(id => [id, {value:'', hidden:false, disabled:false}]));
elements.scenario.value = 'missing';
const tasks = new Map(); let seq = 0;
const context = vm.createContext({document:{getElementById(id){
  if (['play','export'].includes(id)) return elements[id] ||= {};
  assert.ok(elements[id], 'element exists: '+id); return elements[id];
}},setTimeout(fn){tasks.set(++seq, fn); return seq;},clearTimeout(id){tasks.delete(id);}});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], context);
const call = code => vm.runInContext(code, context);
const state = () => JSON.parse(call('JSON.stringify(s)'));
const scenario = value => {elements.scenario.value=value; elements.scenario.onchange();};
const drain = () => {let limit=30; while(tasks.size && --limit){const [id, fn]=tasks.entries().next().value;tasks.delete(id);fn();}assert.ok(limit);};
let cases=0;
for(const value of [...html.matchAll(/<option value="([^"]+)">/g)].map(m=>m[1]).filter(v=>!['total','batch'].includes(v))){
  scenario(value); assert.ok(elements.overall.textContent); cases++;
  elements.reopen.onclick(); assert.equal(elements.method.value,state().method);
}
scenario('missing');assert.equal(elements.overall.textContent,'部分完成');assert.ok(elements.start.disabled);
elements['v-action'].onclick();elements['detail-action'].onclick();assert.equal(state().v,'ready');
elements.start.onclick();assert.equal(state().a,'done');assert.equal(state().current,'v');drain();assert.equal(elements.overall.textContent,'全部要求已完成');
scenario('bmissing');elements.start.onclick();drain();assert.equal(state().a,'done');assert.equal(state().v,'missing');assert.equal(elements.overall.textContent,'部分完成');
scenario('afail');elements.start.onclick();drain();assert.equal(state().a,'failed');assert.equal(state().v,'done');assert.equal(elements.overall.textContent,'部分完成');
scenario('video');elements.start.onclick();assert.equal(state().current,'a');assert.equal(state().v,'waiting');drain();assert.equal(state().v,'done');assert.equal(elements.count.textContent,'1／1 個要求格式完成');
scenario('reuse');elements.start.onclick();assert.equal(state().current,'v');assert.equal(state().a,'done');drain();
scenario('vfail');elements.start.onclick();assert.equal(state().current,'v');elements['cancel-job'].onclick();drain();assert.equal(state().a,'done');assert.equal(state().v,'cancelled');
scenario('disk');elements.start.onclick();drain();assert.equal(state().a,'done');assert.equal(state().v,'failed');
scenario('audio');assert.ok(elements['method-label'].hidden);elements.start.onclick();drain();assert.equal(elements.overall.textContent,'全部要求已完成');
elements.mp3.checked=false;elements.mp3.onchange();assert.ok(elements.start.disabled);assert.equal(elements.overall.textContent,'請選擇輸出格式');
for(const kind of ['a','v','versions','material','joins','settings']){call(`showDetail('${kind}')`);assert.ok(elements['detail-title'].textContent);elements['detail-back'].onclick();assert.equal(call('page'),'home');}
console.log(JSON.stringify({scenarioChecks:cases, behaviorChecks:'passed', syntax:'passed', elementReferences:'passed', browserVisualQA:'not run: local file URL rejected by browser security policy'},null,2));
