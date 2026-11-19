const fs=require('fs'),vm=require('vm'),assert=require('assert');const nodes={};const node=id=>nodes[id]??=( {textContent:'',innerHTML:'',disabled:false,hidden:false,options:[{}],classList:{toggle(){}},setAttribute(){}} );const ctx={document:{getElementById:node,querySelectorAll:()=>[]}};vm.createContext(ctx);const run=s=>vm.runInContext(s,ctx);run(fs.readFileSync(__dirname+'/app.js','utf8'));let count=0;function check(code){run(code);count++}
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
console.log(`PASS ${count} route/handler/state checks; browser geometry and scrolling unverified.`);
