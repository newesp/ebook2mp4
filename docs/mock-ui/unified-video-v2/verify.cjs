const fs=require('fs'),vm=require('vm'),assert=require('assert');const nodes={};const node=id=>nodes[id]??=( {textContent:'',innerHTML:'',disabled:false,hidden:false,options:[{}],classList:{toggle(){}},setAttribute(){}} );let focused='';const tabs=['preview','sources','results'].map(p=>Object.assign(node('tab-'+p),{dataset:{panel:p},setAttribute(k,v){this[k]=v},focus(){focused=p}}));const ctx={document:{getElementById:node,querySelectorAll:()=>tabs}};vm.createContext(ctx);const run=s=>vm.runInContext(s,ctx);run(fs.readFileSync(__dirname+'/app.js','utf8'));let count=0;function check(code){run(code);count++}
for(const k of ['batch','total','merge'])for(const p of ['preview','sources','results']){run(`scope='${k==='batch'?'batch':'book'}';method='${k==='batch'?'total':k}';showPanel('${p}')`);assert(nodes.content.innerHTML.length>100);for(const m of nodes.content.innerHTML.matchAll(/on(?:click|change|input)="([^"]*)"/g)){new vm.Script('(function(){'+m[1].replaceAll('&quot;','"').replaceAll('&#39;',"'").replaceAll('&amp;','&').replaceAll('&lt;','<').replaceAll('&gt;','>')+'})')}count++}
check("scope='batch';states.batch.file='';start()");assert.equal(run('owner'),null);assert.equal(run('s().panel'),'sources');
check("pick();start();setScope('book')");assert.equal(run('scope'),'batch');assert.equal(run('owner'),'batch');
check("finish('done')");assert.equal(run('s().product.version'),1);
check("start();finish('failed')");assert.equal(run('s().product.version'),1);
check("start();finish('pending')");assert.equal(run('owner'),'batch');
check("retrySave()");assert.equal(run('owner'),null);assert.equal(run('s().product.version'),2);
check("states.batch.file='own.png';selectBatch(0);edit('file','first.png');selectBatch(2)");assert.equal(run('s().file'),'own.png');
check("setScope('book');setMethod('merge');start()");assert.equal(run('owner'),null);
check("edit('ack',true);start();finish('cancelled')");assert.equal(run('s().status'),'cancelled');
check("setMethod('total');edit('file','book.png');setScope('batch')");assert.equal(run('s().file'),'own.png');
run("showPanel('preview');tabKey({key:'ArrowRight',preventDefault(){}})");assert.equal(run('s().panel'),'sources');assert.equal(focused,'sources');assert.equal(tabs[1]['aria-selected'],'true');assert.equal(tabs.filter(t=>t.tabIndex===0).length,1);count++;
run("tabKey({key:'End',preventDefault(){}})");assert.equal(run('s().panel'),'results');count++;
run("tabKey({key:'Home',preventDefault(){}});tabKey({key:'ArrowLeft',preventDefault(){}})");assert.equal(run('s().panel'),'results');count++;
run('toggleFiles()');assert.equal(nodes.listToggle.textContent,'<');run('toggleFiles()');assert.equal(nodes.listToggle.textContent,'>');count++;
const html=fs.readFileSync(__dirname+'/index.html','utf8');assert.equal((html.match(/role="tab"/g)||[]).length,3);assert(html.includes('role="tabpanel"'));for(const label of ['狀態詳情','來源與製作設定','>成品</button>'])assert(!html.includes(label));count++;
console.log(`PASS ${count} route/handler/state checks; browser geometry and scrolling unverified.`);
