const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('web/audio.js','utf8').replace('export class CompanionAudio','class CompanionAudio')+'\nthis.CompanionAudio=CompanionAudio;';
const spoken=[],nodes=[],statuses=[];let cancelled=0,created=0,local=false;
class Audio {constructor(){created++;this.state='running';this.currentTime=0;this.destination={};}createOscillator(){const o={frequency:{},connect(){},start(){},stop(){o.stopped=true;},disconnect(){o.disconnected=true;}};nodes.push(o);return o;}createGain(){return {gain:{setValueAtTime(){},linearRampToValueAtTime(){},exponentialRampToValueAtTime(){}},connect(){},disconnect(){}};}async resume(){this.state='running';}async close(){this.closed=true;}}
const window={AudioContext:Audio,SpeechSynthesisUtterance:class {constructor(text){this.text=text;}},speechSynthesis:{getVoices:()=>[{lang:'en-US',localService:false,name:'Remote'},...(local?[{lang:'en-GB',localService:true,name:'Local'}]:[])],speak:u=>spoken.push(u),cancel:()=>cancelled++}};
const scope={window,document:{hidden:false}};vm.runInNewContext(source,scope);const audio=new scope.CompanionAudio(s=>statuses.push(s));
(async()=>{
 audio.say('hello');assert.equal(created,0);assert.equal(spoken.length,0);
 await audio.enable(true);assert.equal(created,1);assert.equal(spoken.length,0,'no default or remote voice fallback');assert.ok(nodes.length>0);
 local=true;audio.say('A stretch invitation.');assert.equal(spoken.length,1);assert.equal(spoken[0].voice.localService,true);
 audio.stop();assert.ok(nodes.every(n=>n.stopped));assert.ok(cancelled>0);
 scope.document.hidden=true;audio.say('Hidden');assert.equal(spoken.length,1);
 scope.document.hidden=false;await audio.enable(false);audio.say('Muted');assert.equal(spoken.length,1);
 await audio.enable(true);audio.dispose();assert.equal(audio.context,null);const count=spoken.length;audio.say('Closed');assert.equal(spoken.length,count);
 // A retired enable may resolve/reject after a newer user choice.
 const deferred=[];
 window.AudioContext=class extends Audio {constructor(){super();this.state='suspended';}resume(){return new Promise((resolve,reject)=>deferred.push({resolve:()=>{this.state='running';resolve();},reject}));}};
 const raced=new scope.CompanionAudio(s=>statuses.push(s));
 const first=raced.enable(true);await raced.enable(false);
 const second=raced.enable(true);deferred[1].resolve();assert.equal(await second,true);assert.equal(raced.enabled,true);
 const status=statuses.at(-1);deferred[0].reject(new Error('old failure'));assert.equal(await first,false);assert.equal(raced.enabled,true);assert.equal(statuses.at(-1),status);
 raced.dispose();
 const stopped=new scope.CompanionAudio(s=>statuses.push(s));
 const pending=stopped.enable(true);stopped.stop();deferred[2].resolve();assert.equal(await pending,false);assert.equal(stopped.enabled,false);
 const before=spoken.length;stopped.say('Cannot speak after canceled enable');assert.equal(spoken.length,before);stopped.dispose();
 const midEnable=new scope.CompanionAudio();const waiting=midEnable.enable(true);const spokenBefore=spoken.length;midEnable.say('Permission event during device activation');assert.equal(spoken.length,spokenBefore);deferred[3].resolve();assert.equal(await waiting,true);assert.equal(midEnable.enabled,true);midEnable.dispose();
 const closed=new scope.CompanionAudio();const wait=closed.enable(true);closed.dispose();deferred[4].resolve();assert.equal(await wait,false);assert.equal(closed.enabled,false);
 console.log('Opt-in audio, local-voice restriction, mute/hidden/disposal cancellation pass.');
})().catch(e=>{console.error(e);process.exitCode=1;});
