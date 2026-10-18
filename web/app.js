import {CompanionAudio} from './audio.js';
const el = id=>document.getElementById(id);
let engine,view,running=false,busy=false,wall=0,simStart=0,frameId=null,generation=0,pageClosed=false;
let audioRequestGeneration=0;
let taskStarting=false;
let companionAudio=new CompanionAudio(text=>{el('audio-status').textContent=text;});
const kinds={qualification:'Controller reference matched',scene_reset:'Fresh scene',action_requested:'Task request',action_allowed:'Permission granted',action_denied:'Request declined',action_started:'Controller acknowledgement',action_outcome:'Measured gesture outcome',action_interrupted:'Task interrupted',skill_started:'Task started',skill_progress:'Task progress',skill_completed:'Measured task result',skill_failed:'Task needs attention',controller_input:'Controller receipt',controller_mode:'Measured controller mode',external_force_applied:'Simulator test started',external_force_removed:'Simulator force removed',observation_interrupted:'Observation unavailable',observation_restored:'Observation restored',measured_alert:'Measured simulator alert'};

function event(e){
  const words={
    action_allowed:e.action==='wave'?'Hello! A little company for your workday.':e.action==='bow'?'Shall we take a little stretch?':e.action==='cup'?'I’ll slide the empty cup to your coaster.':e.action==='cleanup'?'I’ll slide the desk item into its tray.':'',
    action_denied:e.message,
    skill_completed:e.message,
    skill_failed:'I couldn’t finish that. Please check what happened.',
    measured_alert:'Something changed. Please check the desk.'
  };
  if(['action_allowed','action_denied','skill_started','skill_progress','skill_completed','skill_failed','action_interrupted'].includes(e.kind))el('task-message').textContent=e.message;
  if(e.kind==='scene_reset')el('task-message').textContent='Ready when you are. Choose a task.';
  if(words[e.kind])companionAudio.say(words[e.kind],e.kind==='skill_completed'?'complete':e.action==='wave'?'hello':'notice');
  const list=el('timeline');if(!engine?.events?.length||list.firstElementChild?.textContent==='Start the simulation to collect local evidence.')list.replaceChildren();
  const li=document.createElement('li'),time=document.createElement('time'),body=document.createElement('div'),title=document.createElement('strong'),p=document.createElement('p');
  time.textContent=`Scene ${e.episode} · ${e.sim_time_s.toFixed(2)} s`;title.textContent=kinds[e.kind]??e.kind;p.textContent=e.message;body.append(title,p);li.append(time,body);list.prepend(li);
  while(list.children.length>30)list.lastElementChild.remove();
  if(['action_denied','measured_alert','observation_interrupted','observation_restored','scene_reset'].includes(e.kind)){
    el('notice').textContent=e.message;el('notice').parentElement.classList.toggle('alert',['measured_alert','observation_interrupted'].includes(e.kind));
  }
}

function refresh(){
  if(!engine)return;
  const stale=engine.data.time<engine.observationUntil,s=engine.lastObserved;
  el('mode').textContent=stale?'Unknown':engine.skills?.active?(engine.skills.active.action==='cup'?'Bringing the empty cup':'Tidying the desk item'):s.mode==='locomotion'?'Waiting for you':s.mode==='claw_left'?'Settling after a task':s.mode.replaceAll('_',' ');
  el('cancel-task').hidden=!engine.skills?.active;
  el('sim-time').textContent=`${engine.data.time.toFixed(2)} s`;
  el('margin').textContent=stale?'Unknown':`${(s.margin_m*100).toFixed(1)} cm`;
  el('observation').textContent=stale?`Unavailable (${(engine.data.time-engine.lastObservedAt).toFixed(1)} s)`:'Available';
  el('run-label').textContent=running?'Live local physics · MuJoCo 3.11':'Simulation paused';
  el('live-dot').classList.toggle('running',running);el('pause').textContent=running?'Pause simulation':'Resume simulation';
}

async function frame(){
  frameId=null;
  if(!engine||!running||pageClosed)return;
  const current=engine,epoch=generation;
  if(!busy){
    busy=true;
    try{
      // Bound work per animation frame; never overlap asynchronous inferences
      // or jump simulation time forward to hide a slow device.
      const desired=(performance.now()-wall)/1000+simStart;
      for(let i=0;i<6&&running&&epoch===generation&&current.data.time<desired;i++)await current.step();
    }catch(error){if(epoch===generation&&!pageClosed){running=false;el('notice').textContent=error.message;el('notice').parentElement.classList.add('alert');console.error(error);}}
    finally{if(epoch===generation)busy=false;}
  }
  if(epoch!==generation||pageClosed||current!==engine)return;
  view.draw();refresh();if(running)frameId=requestAnimationFrame(frame);
}

function pause(){companionAudio.stop();running=false;if(frameId!==null)cancelAnimationFrame(frameId);frameId=null;refresh();}
function resume(){if(!engine||engine.disposed||pageClosed)return;running=true;wall=performance.now();simStart=engine.data.time;refresh();if(frameId===null&&!busy)frameId=requestAnimationFrame(frame);}

async function startObjectTask(action){
  if(!['cup','cleanup'].includes(action))throw new Error('Unknown object task');
  if(!engine||pageClosed||taskStarting)return {allowed:false,reason:'A task scene is already starting.'};
  if(engine.skills?.active||engine.activeRequest)return engine.request(action);
  const current=engine,epoch=generation;
  taskStarting=true;pause();
  try{
    // Starting an object task is an explicit new episode, never a mid-task
    // reset or an object position edit used to manufacture placement.
    while(busy)await new Promise(resolve=>setTimeout(resolve,10));
    if(epoch!==generation||pageClosed||engine!==current)return {allowed:false,reason:'The page closed before the task scene started.'};
    if(current.skills?.active||current.activeRequest)return current.request(action);
    current.reset();
    const result=current.request(action);
    if(!document.hidden)resume();
    return result;
  }finally{taskStarting=false;if(engine&&!pageClosed)refresh();}
}

function shutdown(){
  audioRequestGeneration++;companionAudio.dispose();pageClosed=true;generation++;running=false;
  if(frameId!==null)cancelAnimationFrame(frameId);frameId=null;
  const retired=engine;engine=null;view?.dispose();view=null;retired?.dispose();
  busy=false;window.jumperDemo=undefined;
}

function restoreStart(){
  pageClosed=false;companionAudio=new CompanionAudio(text=>{el('audio-status').textContent=text;});el('companion-audio').checked=false;el('companion-audio').disabled=true;
  document.querySelectorAll('button').forEach(b=>b.disabled=true);el('start').disabled=false;
  el('start-overlay').hidden=false;el('start-overlay').style.display='grid';
  el('run-label').textContent='Simulation not started';el('live-dot').classList.remove('running');
  el('load-status').textContent='Page restored. Press Start for a fresh local simulation.';
}

el('start').addEventListener('click',async()=>{
  const start=el('start');start.disabled=true;
  const epoch=++generation;
  try{
    const [{Simulation},{DeskRenderer}]=await Promise.all([import('./simulation.js'),import('./render.js')]);
    if(epoch!==generation||pageClosed)return;
    el('timeline').replaceChildren();
    engine=new Simulation(e=>{if(epoch===generation&&!pageClosed)event(e);});
    await engine.load(s=>{if(epoch===generation&&!pageClosed)el('load-status').textContent=s;});
    if(epoch!==generation||pageClosed)return;
    view=new DeskRenderer(el('viewport'),engine,()=>running);
    el('start-overlay').hidden=true;el('start-overlay').style.display='none';
    document.querySelectorAll('button').forEach(b=>b.disabled=false);el('companion-audio').disabled=false;
    document.querySelectorAll('[data-manipulation]').forEach(b=>b.disabled=!engine.config.manipulation?.plans?.[b.dataset.action]?.qualified);
    el('qualification').textContent=`Official controller reference: ${engine.reference.frames} frames, observation error ${engine.reference.observation}, target error ${engine.reference.target}. Browser ONNX reference: ${engine.inferenceReference.frames} frames, maximum absolute error ${engine.inferenceReference.maximum_absolute_error.toExponential(2)}. These checks do not establish hardware performance.`;
    window.jumperDemo={engine,view,pause,resume,startTask:startObjectTask,request:a=>engine.request(a),
      experiment:a=>engine.experiment(a),reset:()=>{companionAudio.stop();engine.reset();resume();},
      advance:async n=>{pause();while(busy)await new Promise(r=>setTimeout(r,10));for(let i=0;i<n;i++)await engine.step();view.draw();refresh();return engine.snapshot();},
      snapshot:()=>({...engine.snapshot(),sim_time_s:engine.data.time,events:engine.events.length}),evidence:()=>engine.evidence()};
    resume();
  }catch(error){
    if(epoch!==generation||pageClosed)return;
    console.error(error);start.disabled=false;el('load-status').textContent=`Could not start: ${error.message}. Try current desktop Chrome with WebGL enabled, or read the source reproduction guide. No recorded animation is substituted.`;
    if(view)view.dispose();engine?.dispose();engine=null;view=null;
  }
});

document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',async()=>{
  if(!engine||taskStarting)return;
  const a=b.dataset.action;
  if(['cup','cleanup'].includes(a))await startObjectTask(a);
  else if(['wave','bow','jump'].includes(a))engine.request(a);else engine.experiment(a);
  refresh();
}));
el('cancel-task').addEventListener('click',()=>{companionAudio.stop();engine.skills?.abort('You ended the task before placement was verified.');refresh();});
el('pause').addEventListener('click',()=>{if(taskStarting)return;if(running)pause();else resume();});
el('reset').addEventListener('click',()=>{if(busy||taskStarting)return;companionAudio.stop();engine.reset();resume();});
el('companion-audio').addEventListener('change',async event=>{const request=++audioRequestGeneration;await companionAudio.enable(event.target.checked);if(request===audioRequestGeneration&&!pageClosed)event.target.checked=companionAudio.enabled;});
el('export').addEventListener('click',()=>{
  const blob=new Blob([JSON.stringify(engine.evidence(),null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='clawmetry-jumper-browser-evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);
});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&engine){pause();engine.fsm.letGo(engine.tick*5000);}});
window.addEventListener('pagehide',shutdown);
window.addEventListener('pageshow',e=>{if(e.persisted)restoreStart();});
