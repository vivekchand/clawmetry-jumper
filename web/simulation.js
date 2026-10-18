import {DeskSkills} from './manipulation.js';
import loadMujoco from './vendor/mujoco/mujoco.js';
import * as ort from './vendor/ort/ort.wasm.min.mjs';
import initController, {WebFsm} from './assets/bundle/runtime/web/controller.js';

const ROOT = new URL('./assets/', import.meta.url);
const fetchBytes = async (url, signal) => {
  const r = await fetch(url,{signal}); if (!r.ok) throw new Error(`Asset could not load (${r.status}): ${url}`);
  return new Uint8Array(await r.arrayBuffer());
};
const fetchText = async (path, signal) => new TextDecoder().decode(await fetchBytes(new URL(path, ROOT),signal));
const finite = (xs) => Array.from(xs).every(Number.isFinite);
const f32 = (xs) => Float32Array.from(xs);
const digest = async (bytes) => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2,'0')).join('');

export class Simulation {
  constructor(onEvent = () => {}) {
    this.onEvent = onEvent; this.events = []; this.samples = []; this.sequence = 0;
    this.tick = 0; this.inferences = 0; this.paused = true; this.pending = [];
    this.lastObserved = null; this.alertFlags = new Set(); this.observationUntil = 0;
    this.sampleCount = 0; this.truncated = false; this.episode = 0;
    this.disposed=false;this.abort=new AbortController();this.activeInference=null;
  }

  assertAlive(){if(this.disposed)throw new Error('Simulation closed');}

  emit(kind, message, extra = {}) {
    const e = {sequence: ++this.sequence, episode:this.episode, sim_time_s: this.data?.time ?? 0, kind, message, ...extra};
    this.events.push(e); if (this.events.length > 1000) {this.events.shift(); this.truncated=true;}
    this.onEvent(e); return e;
  }

  async load(status) {
    const signal=this.abort.signal;
    status('Loading the fixed robot, scene and public runtimes…');
    this.config = JSON.parse(await fetchText('config.json',signal));
    if (this.config.mujoco_version !== '3.11.0') throw new Error('Unsupported engine asset version');
    this.mj = await loadMujoco();
    this.assertAlive();
    this.vfs = new this.mj.MjVFS();
    const xml = await fetchBytes(new URL('model.xml', ROOT),signal);
    if (await digest(xml) !== this.config.model_sha256) throw new Error('Model asset integrity mismatch');
    this.vfs.addBuffer('model.xml', xml);
    let loaded = 0;
    await Promise.all(this.config.vfs.map(async r => {
      const bytes = await fetchBytes(new URL(r.path, ROOT),signal);
      if (bytes.length !== r.bytes || await digest(bytes) !== r.sha256) throw new Error(`Asset integrity mismatch: ${r.path}`);
      this.assertAlive();
      this.vfs.addBuffer(r.path, bytes); loaded++;
      if (loaded % 15 === 0) status(`Loading robot resources: ${loaded}/${this.config.vfs.length}`);
    }));
    this.assertAlive();this.model = this.mj.MjModel.from_xml_path('model.xml', this.vfs);
    this.data = new this.mj.MjData(this.model);
    if (this.model.ngeom !== this.config.counts.ngeom || this.model.nq !== this.config.counts.nq) throw new Error('Browser model structure differs from prepared model');
    this.manifest = JSON.parse(await fetchText('bundle/bundle.json',signal));
    this.contracts = {}; this.trajectories = {};
    for (const [mode, entry] of Object.entries(this.manifest.modes)) {
      this.contracts[mode] = JSON.parse(await fetchText(`bundle/${entry.contract}`,signal));
      if (entry.trajectory) this.trajectories[mode] = await fetchText(`bundle/${entry.trajectory}`,signal);
    }
    this.fsmText = await fetchText('bundle/controller.toml',signal);
    const wasm = await fetchBytes(new URL('bundle/runtime/web/controller.wasm', ROOT),signal);
    await initController({module_or_path: wasm.buffer});
    this.assertAlive();this.referenceText = await fetchText('bundle/reference.json',signal);
    const verifier = this.newController();
    try {this.reference = JSON.parse(verifier.checkReference(this.referenceText));} finally {verifier.free();}
    const mismatch = this.reference.modeMismatches ?? this.reference.mode_mismatches ?? [];
    if (this.reference.observation > 1e-6 || this.reference.target > 1e-6 || mismatch.length || this.reference.divergent?.length) throw new Error('Official controller reference did not agree');
    ort.env.wasm.numThreads = 1;
    ort.env.wasm.proxy = false;
    ort.env.wasm.wasmPaths = new URL('./vendor/ort/', import.meta.url).href;
    this.sessions = new Map();
    status('Checking browser policy inference…');
    this.inferenceReference = await this.checkInference();
    this.reset();
    this.emit('qualification', 'Official controller reference and browser inference checks passed.', {
      controller_reference: this.reference, inference_reference: this.inferenceReference,
      engine: 'MuJoCo WASM 3.11.0', model_sha256: this.config.model_sha256,
      model_counts: this.config.counts, upstream_commit: this.config.upstream_commit});
    return this;
  }

  newController() {
    const c = this.contracts.locomotion, wire = this.config.wire;
    return new WebFsm(this.fsmText, JSON.stringify(this.contracts), JSON.stringify({
      joint_names: wire, joint_pos_lo: wire.map(n => c.joint_limits[n][0]),
      joint_pos_hi: wire.map(n => c.joint_limits[n][1]), output_rate_hz: 200}), 0, JSON.stringify(this.trajectories));
  }

  async session(mode) {
    this.assertAlive();
    const path = this.manifest.modes[mode]?.models?.onnx;
    if (!path) throw new Error(`No official policy for ${mode}`);
    if (!this.sessions.has(path)) {
      const candidate=await ort.InferenceSession.create(new URL(`bundle/${path}`, ROOT).href,
        {executionProviders:['wasm'], graphOptimizationLevel:'all'});
      if(this.disposed){await candidate.release();throw new Error('Simulation closed');}
      this.sessions.set(path,candidate);
    }
    return this.sessions.get(path);
  }

  async infer(mode, observation) {
    const session = await this.session(mode);
    this.assertAlive();
    const pending=session.run({[session.inputNames[0]]: new ort.Tensor('float32', f32(observation), [1,observation.length])});
    this.activeInference=pending;
    let result;
    try{result=await pending;this.assertAlive();}finally{if(this.activeInference===pending)this.activeInference=null;}
    const action = result[session.outputNames[0]].data;
    if (!finite(action)) throw new Error('Policy returned a nonfinite action');
    return action;
  }

  async checkInference() {
    const frames = JSON.parse(this.referenceText).frames.filter(f => f.obs && f.act);
    let maximum = 0;
    for (const frame of frames) {
      const act = await this.infer(frame.mode, frame.obs);
      if (act.length !== frame.act.length) throw new Error('Policy output shape differs from reference');
      maximum = Math.max(maximum, ...act.map((x,i) => Math.abs(x-frame.act[i])));
    }
    if (!frames.length || maximum > 2e-5) throw new Error(`Browser inference reference failed: ${maximum}`);
    return {frames:frames.length, maximum_absolute_error:maximum, tolerance:2e-5, passed:true};
  }

  reset() {
    this.assertAlive();
    this.skills?.abort('The scene reset before placement was verified.');
    if(this.activeRequest)this.emit('action_interrupted','The scene was reset before the requested gesture had a measured return.',{request_id:this.activeRequest.request_id,outcome:'interrupted'});
    this.episode++;
    this.fsm?.free(); this.fsm = this.newController();
    this.mj.mj_resetData(this.model, this.data);
    this.data.qpos.set(this.config.initial_qpos);
    this.data.qvel.fill(0); this.data.qfrc_applied.fill(0); this.data.xfrc_applied.fill(0);
    this.mj.mj_forward(this.model,this.data);
    this.torque = new Float64Array(this.config.wire.length);
    this.heat = new Float64Array(this.config.wire.length); this.tick=0;
    this.pending=[]; this.force=null; this.observationUntil=0; this.alertFlags.clear();this.activeRequest=null;this.hasAcceptedRequest=false;
    this.skills=this.config.manipulation?new DeskSkills(this,this.config.manipulation):null;
    this.minMargin=Infinity; this.lastObserved=this.snapshot(); this.lastObservedAt=0;
    this.emit('scene_reset','Fresh scene started at the documented controller home pose.');
  }

  request(action) {
    const requestId = crypto.randomUUID();
    if (!['wave','bow','jump','cup','cleanup'].includes(action)) throw new Error('Unknown task request');
    const manipulation=['cup','cleanup'].includes(action);
    this.emit('action_requested', `Requested: ${action}.`, {request_id:requestId, action, task:manipulation?(action==='cup'?'empty_cup_to_coaster':'desk_item_to_tray'):'desk_reminder'});
    let reason = '';
    if (this.data.time < this.observationUntil) reason='Observation unavailable. New actions need fresh evidence.';
    else if (action === 'jump') reason='A jump is outside this reminder task.';
    else if(this.skills?.active||this.activeRequest) reason='Let me finish this little task first, or end it.';
    else if(manipulation&&this.data.time>3)reason='Use Start cup task or Start cleanup task for a fresh scene.';
    else if(manipulation&&this.hasAcceptedRequest)reason='Start a fresh scene for this fixed-scene object task.';
    else if(manipulation) reason=this.skills?.reason(action)??'This scene has no qualified object task.';
    if(!reason && (this.pending.length || (manipulation?!['locomotion','claw_left'].includes(this.fsm.mode()):this.fsm.mode() !== 'locomotion'))) reason='Wait for the current motion to return before requesting another.';
    if(!reason && (this.snapshot().margin_m < .12 || this.snapshot().tilt_deg > 35)) reason='The current measured pose needs a fresh scene before a greeting.';
    if (reason) {
      this.emit('action_denied',reason,{request_id:requestId,action,forwarded:false}); return {allowed:false,reason,request_id:requestId};
    }
    this.hasAcceptedRequest=true;
    if(manipulation){
      this.emit('action_allowed',action==='cup'?'Empty cup to the coaster allowed.':'Named desk item to the tray allowed.',{request_id:requestId,action});
      this.skills.start(action,requestId);return {allowed:true,request_id:requestId};
    }
    const code = action === 'wave' ? 'Digit1' : 'Digit2';
    this.pending.push({code,down:true,at:this.data.time,requestId,action},
                      {code,down:false,at:this.data.time+.04,requestId,action});
    this.activeRequest={request_id:requestId,action,mode:action==='wave'?'gesture_hello':'gesture_bow',started:false,feed_complete:true,minimum_margin_m:Infinity,maximum_tilt_deg:0};
    this.emit('action_allowed',`${action === 'wave' ? 'Greeting' : 'Stretch invitation'} allowed for this task.`,{request_id:requestId,action});
    return {allowed:true,request_id:requestId};
  }

  queueKey(code,requestId,action){this.pending.push({code,down:true,at:this.data.time,requestId,action},{code,down:false,at:this.data.time+.04,requestId,action});}

  experiment(kind) {
    if(!['stale','lift','drift'].includes(kind))throw new Error('Unknown experiment');
    this.skills?.abort(kind==='stale'?'Observations were interrupted. Placement is unknown.':'A disturbance interrupted the task before placement was verified.',kind==='stale'?'unknown':'interrupted');
    if (kind === 'stale') {
      this.observationUntil = this.data.time+3;
      this.emit('observation_interrupted','The ClawMetry observation feed is paused for three simulated seconds. Native physics and controller continue.',{duration_s:3}); return;
    }
    if (!['lift','drift'].includes(kind)) throw new Error('Unknown experiment');
    if (this.force) return;
    this.force = {kind, until:this.data.time+.35, vector:kind==='lift'?[0,0,45]:[45,0,0]};
    this.emit('external_force_applied',`Scripted ${kind === 'lift' ? 'lifting' : 'sideways'} wrench applied to the simulated body.`,{force_n:this.force.vector,duration_s:.35});
  }

  async step() {
    this.assertAlive();
    if (!finite(this.data.qpos) || !finite(this.data.qvel)) throw new Error('Physics became nonfinite. Reset the simulation.');
    const now = this.tick*5000, c=this.config, q=this.data.qpos, v=this.data.qvel;
    const quat=this.data.xquat.subarray(c.base_body*4,c.base_body*4+4);
    const gyro=this.data.sensordata.subarray(c.gyro_adr,c.gyro_adr+3);
    this.fsm.set_state(f32(c.qadr.map(i=>q[i])),f32(c.dadr.map(i=>v[i])),f32(this.torque),f32(quat),f32(gyro),now);
    this.fsm.setSignal('base_lin_vel',f32(this.data.sensordata.subarray(c.velocity_adr,c.velocity_adr+3)));
    this.fsm.set_command(0,0,0,now);
    const ready=this.pending.filter(e=>e.at<=this.data.time+1e-9);
    this.pending=this.pending.filter(e=>e.at>this.data.time+1e-9);
    for(const e of ready) {
      const accepted=this.fsm.setKeyCode(e.code,e.down,false,now);
      if(e.down) this.emit('controller_input',`Official controller ${accepted?'bound':'did not bind'} the ${e.action} request.`,{request_id:e.requestId,key:e.code,bound:accepted});
    }
    const previous=this.fsm.mode(), mode=this.fsm.tick(now);
    if(mode!==undefined) {const action=await this.infer(mode,this.fsm.observation());this.assertAlive();this.fsm.resume(action);this.inferences++;}
    const target=this.fsm.positions(), kp=this.fsm.kp(), kd=this.fsm.kd(), s=c.servo;
    const skillTargets=this.skills?.targets();
    if(skillTargets){
      for(let k=0;k<skillTargets.length;k++){
        const i=c.manipulation.wire_indices[k],limits=this.contracts.locomotion.joint_limits[c.wire[i]],value=skillTargets[k];
        if(!Number.isFinite(value)||value<limits[0]-1e-6||value>limits[1]+1e-6)throw new Error('The task target exceeds the original joint limits. Start a fresh scene.');
        target[i]=k===4?Math.min(value,q[c.qadr[i]]+.06):value;kp[i]=10;kd[i]=.5;
      }
    }
    const thermal=s.peak_duration_s / Math.log(1/(1-(s.thermal_continuous_torque_nm/s.plateau_torque_nm)**2));
    for(let sub=0;sub<5;sub++) {
      this.data.qfrc_applied.fill(0);this.data.xfrc_applied.fill(0);
      for(let j=0;j<c.wire.length;j++) {
        const speed=Math.abs(v[c.dadr[j]]),rpm=2*Math.PI/60;
        let curve=s.plateau_torque_nm*Math.exp(-Math.max(speed-s.corner_speed_rpm*rpm,0)/(s.decay_speed_rpm*rpm));
        if(speed>=s.cutoff_speed_rpm*rpm)curve=0;
        const limit=Math.min(curve,this.heat[j]>=1?s.thermal_continuous_torque_nm:s.plateau_torque_nm);
        const raw=kp[j]*(target[j]-q[c.qadr[j]])-kd[j]*v[c.dadr[j]];
        this.torque[j]=Math.max(-limit,Math.min(limit,raw));
        this.heat[j]=Math.max(0,this.heat[j]+((this.torque[j]/s.thermal_continuous_torque_nm)**2-this.heat[j])*(.001/thermal));
        this.data.qfrc_applied[c.dadr[j]]=this.torque[j];
      }
      if(this.force && this.data.time<this.force.until) this.data.xfrc_applied.set(this.force.vector,c.base_body*6);
      this.mj.mj_step(this.model,this.data);
    }
    this.mj.mj_forward(this.model,this.data);this.tick++;
    if(this.force && this.data.time>=this.force.until) {
      this.data.xfrc_applied.fill(0);this.emit('external_force_removed','The scripted force is removed. Subsequent movement is the measured physics outcome.',{experiment:this.force.kind});this.force=null;
    }
    const current=this.fsm.mode();
    if(current!==previous)this.emit('controller_mode',`Controller entered ${current.replaceAll('_',' ')}.`,{from:previous,to:current,request_id:this.activeRequest?.request_id??this.skills?.active?.request_id??null});
    const snap=this.snapshot();
    if(this.activeRequest){
      const a=this.activeRequest;
      const observed=this.data.time>=this.observationUntil;
      if(!observed)a.feed_complete=false;
      if(current===a.mode&&!a.started){a.started=true;this.emit('action_started','The official controller entered the requested gesture mode.',{request_id:a.request_id,mode:current});}
      if(a.started&&observed){a.minimum_margin_m=Math.min(a.minimum_margin_m,snap.margin_m);a.maximum_tilt_deg=Math.max(a.maximum_tilt_deg,snap.tilt_deg);}
      if(a.started&&current==='locomotion'){
        this.emit('action_outcome',a.feed_complete?'The gesture controller returned to locomotion. Its measured simulator outcome is recorded.':'The controller returned, but missing observations leave the complete physical outcome unknown.',{
          request_id:a.request_id,outcome:!a.feed_complete?'unknown':a.minimum_margin_m>=0?'returned_within_observed_boundary':'returned_with_boundary_violation',
          feed_complete:a.feed_complete,minimum_observed_margin_m:Number.isFinite(a.minimum_margin_m)?a.minimum_margin_m:null,
          maximum_observed_tilt_deg:a.maximum_tilt_deg,final_measurement:observed?snap:null});
        this.activeRequest=null;
      }
    }
    if(this.data.time>=this.observationUntil) {
      if(this.observationUntil) {this.emit('observation_restored','The observation feed is available again.');this.observationUntil=0;}
      this.lastObserved=snap;this.lastObservedAt=this.data.time;this.minMargin=Math.min(this.minMargin,snap.margin_m);
      for(const [key,test,message] of [
        ['breach',snap.breached,'Measured robot footprint crossed the tabletop boundary. Containment is not guaranteed.'],
        ['edge',snap.margin_m<.12 && !snap.breached,'Measured robot footprint is close to the desk edge.'],
        ['tilt',snap.tilt_deg>35,'Large body tilt measured in simulation.'],
        ['lift',snap.position_m[2]>.23,'Raised body position measured. This is not person or grasp detection.']]) {
        if(test && !this.alertFlags.has(key)) {this.alertFlags.add(key);this.emit('measured_alert',message,{alert:key,measurement:snap});}
      }
    }
    if(this.tick%20===0) {
      this.sampleCount++;
      this.samples.push({episode:this.episode,sim_time_s:this.data.time,observation_available:!this.observationUntil,
        ...(this.observationUntil?{outcome:'unknown'}:snap)});
      if(this.samples.length>6000){this.samples.shift();this.truncated=true;}
    }
    return snap;
  }

  snapshot() {
    const c=this.config, pos=this.data.xpos.subarray(c.base_body*3,c.base_body*3+3);
    const rot=this.data.xmat.subarray(c.base_body*9,c.base_body*9+9);
    const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
    for(const id of c.robot_collision_geoms) {
      const a=c.collision_local_aabb[id], r=this.data.geom_xmat.subarray(id*9,id*9+9), p=this.data.geom_xpos.subarray(id*3,id*3+3);
      for(let ax=0;ax<3;ax++) {
        let center=p[ax], half=0;
        for(let k=0;k<3;k++){center+=r[ax*3+k]*a[k];half+=Math.abs(r[ax*3+k])*a[k+3];}
        lo[ax]=Math.min(lo[ax],center-half);hi[ax]=Math.max(hi[ax],center+half);
      }
    }
    const margin=Math.min(lo[0]+.86,.86-hi[0],lo[1]+.58,.58-hi[1]);
    return {position_m:Array.from(pos),tilt_deg:Math.acos(Math.max(-1,Math.min(1,rot[8])))*180/Math.PI,
      margin_m:margin,breached:margin<0,collision_aabb_m:{min:lo,max:hi},
      mode:this.fsm?.mode()??'initializing',...(this.skills?{objects:this.skills.objects()}:{}),finite:finite(this.data.qpos)&&finite(this.data.qvel)};
  }

  evidence() {
    return {schema:'clawmetry_jumper_browser/1',simulation_only:true,public_data_leaves_device:false,
      model_sha256:this.config.model_sha256,upstream_commit:this.config.upstream_commit,
      engine:'MuJoCo WASM 3.11.0',controller_reference:this.reference,inference_reference:this.inferenceReference,
      current_episode:this.episode,sim_time_s:this.data.time,inferences:this.inferences,control_ticks:this.tick,
      minimum_observed_margin_m:Number.isFinite(this.minMargin)?this.minMargin:null,
      sample_rate_hz:10,monitor_rate_hz:200,total_sample_count:this.sampleCount,truncated:this.truncated,
      events:this.events,samples:this.samples};
  }

  dispose() {
    if(this.disposed)return;
    this.disposed=true;this.abort.abort();
    const sessions=Array.from(this.sessions?.values()??[]);this.sessions?.clear();
    // A session must outlive an inference already in flight. Its completion
    // cannot resume this disposed controller because infer/step check lifetime.
    const wait=this.activeInference??Promise.resolve();
    this.disposal=Promise.allSettled([wait]).then(()=>Promise.allSettled(sessions.map(s=>Promise.resolve().then(()=>s.release()))));
    this.fsm?.free(); this.fsm=null;
    this.data?.delete(); this.data=null;
    this.model?.delete(); this.model=null;
    this.vfs?.delete(); this.vfs=null;
  }
}
