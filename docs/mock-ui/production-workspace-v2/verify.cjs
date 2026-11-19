const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes=new Map();
const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',value:'',hidden:false,dataset:{},classList:{toggle(){}},setAttribute(){}});return nodes.get(id)};
const ctx={console,document:{getElementById:node,querySelectorAll:()=>[]},setTimeout:fn=>fn(),clearTimeout(){}};
ctx.window=ctx;vm.createContext(ctx);
for(const f of ['app.js','voice.js','video.js'])vm.runInContext(fs.readFileSync(__dirname+'/'+f,'utf8'),ctx,{filename:f});
const run=s=>vm.runInContext(s,ctx);let checks=0;
for(const p of ['map','voice','services','defaults','packages','audio','taskinfo','block','restart','manuscript','video','merge','joins','versions']){
  run(`go('${p}')`);assert(node('title').textContent);assert(node('content').innerHTML);
  for(const match of (node('content').innerHTML+node('actions').innerHTML).matchAll(/on(?:click|change|input)="([^"]*)"/g)){
    const code=match[1].replaceAll('&quot;','"').replaceAll('&#39;',"'").replaceAll('&lt;','<').replaceAll('&gt;','>').replaceAll('&amp;','&');
    new vm.Script('(function(){'+code+'})');
  }checks++;
}
run("S.taskState='ready';S.consent=false;S.reuse=false;audioStart()");assert.equal(ctx.S.taskState,'ready');checks++;
run("S.consent=true;audioStart();go('voice')");assert.equal(ctx.S.taskState,'running');assert(ctx.S.projectBusy);checks++;
run("audioFinish();S.taskState='failed';go('audio')");assert(ctx.S.oldProduct);assert(node('content').innerHTML.includes('上一版成功成品'));checks++;
run("S.taskState='ready';S.video.batch.state='running';audioStart()");assert.equal(ctx.S.taskState,'ready');assert(ctx.S.projectBusy);checks++;
run("returnActiveTask()");assert(node('title').textContent.includes('影片'));checks++;
run("S.video.batch.state='ready';S.taskState='pending';go('audio')");assert(node('actions').innerHTML.includes('重試保存'));checks++;
run("S.taskState='ready';S.voice.saved.service='edge';S.voice.draft.service='kokoro'");assert(run('cloudNeeded()'));checks++;
run("S.voice.saved.service='kokoro'");assert(!run('cloudNeeded()'));checks++;
run("S.voice.saved.service='edge';S.reuse=true");assert(!run('cloudNeeded()'));checks++;
run("S.reuse=false;S.merge.selected=[1,2];S.merge.valid=[false,true,true];S.merge.formats=['mp3','mp4'];S.video.total.material='cover.png';S.merge.state='ready';mergeStart();mergeFinish('partial')");assert.equal(ctx.S.merge.results.mp3,'done');assert.equal(ctx.S.merge.results.mp4,'failed');checks++;
run("mergeStart()");assert.deepEqual(Array.from(ctx.S.merge.work),['mp4']);run("mergeFinish('done')");checks++;
console.log(`PASS: ${checks} route, handler syntax and state checks. No browser layout or real media validation.`);
