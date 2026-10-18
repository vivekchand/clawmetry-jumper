const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const text=fs.readFileSync('web/app.js','utf8');
const source=text.slice(text.indexOf('async function startObjectTask('),text.indexOf('\nfunction shutdown()'));
function fixture(){
 let resets=0,resumes=0,requests=0;
 const engine={skills:{active:null},activeRequest:null,reset(){resets++;},request(){requests++;return {allowed:!this.activeRequest&&!this.skills.active};}};
 const context={engine,generation:1,pageClosed:false,taskStarting:false,busy:false,document:{hidden:false},pause(){},resume(){resumes++;},refresh(){},setTimeout};
 vm.runInNewContext(source,context);
 return {engine,context,counts:()=>({resets,resumes,requests})};
}
(async()=>{
 for(const kind of ['activeRequest','skill']){
  const f=fixture();if(kind==='skill')f.engine.skills.active={};else f.engine.activeRequest={};
  assert.equal((await f.context.startObjectTask('cup')).allowed,false);assert.equal(f.counts().resets,0);
 }
 let f=fixture();assert.equal((await f.context.startObjectTask('cup')).allowed,true);assert.equal(f.counts().resets,1);assert.equal(f.counts().resumes,1);
 f=fixture();f.context.busy=true;
 const first=f.context.startObjectTask('cleanup');assert.equal((await f.context.startObjectTask('cup')).allowed,false);
 f.engine.activeRequest={};f.context.busy=false;assert.equal((await first).allowed,false);assert.equal(f.counts().resets,0,'recheck overlap after draining inference');
 f=fixture();f.context.busy=true;
 const closed=f.context.startObjectTask('cup');f.context.pageClosed=true;f.context.generation++;f.context.busy=false;
 assert.equal((await closed).allowed,false);assert.equal(f.counts().resets,0,'closed page cannot reset a retired engine');
 f=fixture();f.context.document.hidden=true;await f.context.startObjectTask('cup');assert.equal(f.counts().resumes,0,'hidden page stays paused');
 console.log('Explicit fresh-scene ownership, overlap, inference draining and page retirement pass.');
})().catch(e=>{console.error(e);process.exitCode=1;});
