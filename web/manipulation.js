/* Scripted simulation skills: joint targets only; all prop motion is physics. */
const WALK_KEYS=new Set(['KeyW','KeyS','KeyA','KeyD']);
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const distance=(a,b)=>Math.hypot(...a.map((x,i)=>x-b[i]));

export class DeskSkills {
  constructor(simulation,config){this.sim=simulation;this.config=config;this.active=null;this.lastResult=null;}
  objects(){
    const d=this.sim.data,result={};
    for(const [name,c] of Object.entries(this.config?.objects??{})){
      const p=Array.from(d.xpos.subarray(c.body_id*3,c.body_id*3+3));
      const r=Array.from(d.xmat.subarray(c.body_id*9,c.body_id*9+9));
      const v=Array.from(d.qvel.subarray(c.dof_adr,c.dof_adr+6));
      const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];let circleFits=true;
      for(const id of c.geom_ids){
        const box=c.local_aabb?.[id];if(!box)continue;
        const rotation=d.geom_xmat.subarray(id*9,id*9+9),position=d.geom_xpos.subarray(id*3,id*3+3);
        const shape=c.geometry?.[id],sphere=shape?.type===2;
        for(let axis=0;axis<3;axis++){let center=position[axis],half=0;
          if(sphere)half=shape.size[0];
          else for(let k=0;k<3;k++){center+=rotation[axis*3+k]*box[k];half+=Math.abs(rotation[axis*3+k])*box[k+3];}
          lo[axis]=Math.min(lo[axis],center-half);hi[axis]=Math.max(hi[axis],center+half);
        }
        if(c.target_shape==='circle'){
          const [x,y]=c.target_xy,limit=c.target_radius_m;
          if(sphere)circleFits&&=Math.hypot(position[0]-x,position[1]-y)+shape.size[0]<=limit;
          else if(shape?.type===5){
            // Upright cylinder disk plus a conservative projected half-height.
            circleFits&&=Math.hypot(position[0]-x,position[1]-y)+shape.size[0]+shape.size[1]*Math.hypot(rotation[2],rotation[5])<=limit;
          }else{
            // Test each actual wall's containing box, not corners of the
            // aggregate cup AABB where there is no material.
            for(const sx of [-1,1])for(const sy of [-1,1])for(const sz of [-1,1]){
              const local=[box[0]+sx*box[3],box[1]+sy*box[4],box[2]+sz*box[5]];
              const px=position[0]+local.reduce((sum,v,k)=>sum+rotation[k]*v,0);
              const py=position[1]+local.reduce((sum,v,k)=>sum+rotation[3+k]*v,0);
              circleFits&&=Math.hypot(px-x,py-y)<=limit;
            }
          }
        }
      }
      const center=c.target_center_xy??c.target_xy;
      const targetContained=c.target_shape==='circle'?circleFits:c.target_shape==='box'&&[0,1].every(i=>lo[i]>=center[i]-c.target_half_size_m[i]&&hi[i]<=center[i]+c.target_half_size_m[i]);
      result[name]={position_m:p,bounds_m:{min:lo,max:hi},target_contained:targetContained,tilt_deg:Math.acos(Math.max(-1,Math.min(1,r[8])))*180/Math.PI,
        linear_speed_m_s:Math.hypot(...v.slice(0,3)),angular_speed_rad_s:Math.hypot(...v.slice(3)),finite:[...p,...r,...v].every(finite)};
    }
    return result;
  }
  contact(name){
    const object=new Set(this.config.objects[name].geom_ids),jaws=new Set(this.config.jaw_geom_ids??[]);
    const robot=new Set(this.sim.config.robot_collision_geoms??this.config.jaw_geom_ids??[]);
    const contacts=this.sim.data.contact;let count=0,robotCount=0;
    try{for(let i=0;i<contacts.size();i++){
      const item=contacts.get(i);if(!item)continue;
      try{if(item.dist<=.001){if((object.has(item.geom1)&&jaws.has(item.geom2))||(object.has(item.geom2)&&jaws.has(item.geom1)))count++;
        if((object.has(item.geom1)&&robot.has(item.geom2))||(object.has(item.geom2)&&robot.has(item.geom1)))robotCount++;}}
      finally{item.delete();}
    }}finally{contacts.delete();}
    return {jaw:count,robot:robotCount};
  }
  reason(action){
    const p=this.config?.plans?.[action];
    if(this.config?.schema!=='mizu_contact_skills/1'||!p?.qualified)return 'This scene has no qualified object task. Start a fresh supported scene.';
    if(this.active)return 'Let me finish this little task first, or end it.';
    if(!['locomotion','claw_left'].includes(this.sim.fsm.mode()))return 'Let the current gesture finish first.';
    if(this.sim.data.time<this.sim.observationUntil)return 'I need fresh observations before moving an object.';
    const object=this.objects()[p.object];
    if(!object?.finite)return 'I cannot confirm the object position.';
    const start=this.config.objects[p.object].start_position_m;
    if(p.pickup_xy_tolerance_m!==undefined&&(Math.hypot(object.position_m[0]-start[0],object.position_m[1]-start[1])>p.pickup_xy_tolerance_m||Math.abs(object.position_m[2]-start[2])>(p.pickup_z_tolerance_m??.012)))return 'The object moved from its tested starting spot. Start a fresh scene before this task.';
    if(distance(object.position_m,this.config.objects[p.object].start_position_m)>(p.pickup_tolerance_m??.012))return 'The object moved from its tested starting spot. Start a fresh scene before this task.';
    if((p.upright_required!==false&&object.tilt_deg>10)||object.linear_speed_m_s>.03)return 'Let the object settle upright first.';
    if(!Array.isArray(p.stages)||!p.stages.length||p.stages.some(stage=>!finite(stage.duration_s)||stage.duration_s<=0||!Array.isArray(stage.joint_targets)||stage.joint_targets.length!==this.config.joint_names.length||!stage.joint_targets.every(finite)||!Array.isArray(stage.native_keys??[])||(stage.native_keys??[]).some(key=>!WALK_KEYS.has(key))||(stage.native_key_hold_s!==undefined&&(!finite(stage.native_key_hold_s)||stage.native_key_hold_s<0||stage.native_key_hold_s>stage.duration_s))))return 'The object task could not be loaded. Start a fresh scene.';
    return '';
  }
  start(action,requestId){
    const reason=this.reason(action);if(reason)return {allowed:false,reason};
    const plan=this.config.plans[action],objects=this.objects();
    this.active={action,request_id:requestId,plan,phase:-1,started:this.sim.data.time,stageAt:this.sim.data.time,
      contacts:0,contactSamples:0,lastContactAt:-Infinity,maximumDisplacement:0,minimumMargin:Infinity,maximumTilt:0,
      initial:objects,stableSince:null,completeFeed:true,ownedKeys:new Set()};
    this.active.entrySent=this.sim.fsm.mode()==='claw_left';
    this.active.supportAt=this.active.entrySent?this.sim.data.time:null;
    this.sim.emit('skill_started',action==='cup'?'Getting ready to slide your empty cup closer.':'Getting ready to put the desk item in its tray.',{request_id:requestId,action,controller_kind:this.config.controller_kind});
    return {allowed:true};
  }
  finish(outcome,message,measurement){
    const a=this.active;if(!a)return;
    this.lastResult={request_id:a.request_id,action:a.action,outcome,measurement,contact_samples:a.contactSamples,
      contact_count:a.contacts,maximum_displacement_m:a.maximumDisplacement,minimum_margin_m:Number.isFinite(a.minimumMargin)?a.minimumMargin:null,
      maximum_robot_tilt_deg:a.maximumTilt,controller_kind:this.config.controller_kind};
    this.active=null;
    // Retire a queued entry even if cancellation races the first key edge.
    // Release a held key before any explicit native return toggle.
    this.sim.pending=this.sim.pending.filter(event=>event.requestId!==a.request_id);
    for(const code of ['KeyV',...a.ownedKeys])this.sim.pending.push({code,down:false,at:this.sim.data.time,requestId:a.request_id,action:a.action});
    this.sim.emit(outcome==='completed'?'skill_completed':'skill_failed',message,this.lastResult);
    if(this.sim.fsm.mode()==='claw_left')this.sim.queueKey('KeyV',a.request_id,a.action);
  }
  abort(message='The task ended before a measured placement.',outcome='interrupted'){
    if(this.active)this.finish(outcome,message,this.objects()[this.active.plan.object]);
  }
  targets(){
    const a=this.active;if(!a)return null;
    const now=this.sim.data.time,c=this.config,objects=this.objects(),object=objects[a.plan.object],state=this.sim.snapshot();
    if(now<this.sim.observationUntil){this.abort('Observations were interrupted. Placement is unknown.','unknown');return null;}
    if(!object?.finite||!state.finite){this.abort('The task stopped because measurements were invalid.','unknown');return null;}
    a.minimumMargin=Math.min(a.minimumMargin,state.margin_m);a.maximumTilt=Math.max(a.maximumTilt,state.tilt_deg);
    a.maximumDisplacement=Math.max(a.maximumDisplacement,distance(object.position_m,a.initial[a.plan.object].position_m));
    const bounds=object.bounds_m;
    if(!bounds.min.every(finite)||!bounds.max.every(finite)||bounds.min[0]<-.86||bounds.max[0]>.86||bounds.min[1]<-.58||bounds.max[1]>.58){this.abort('The object moved beyond the tabletop boundary.','failed');return null;}
    if(state.margin_m<.04||state.tilt_deg>25||(a.plan.upright_required!==false&&object.tilt_deg>30)||object.position_m[2]<-.01){this.abort('The object or robot moved outside the tested task conditions.','failed');return null;}
    for(const [name,other] of Object.entries(objects)){
      if(name!==a.plan.object&&distance(other.position_m,a.initial[name].position_m)>.015){this.abort('Another desk object moved. The task needs a fresh scene.','failed');return null;}
    }
    if(now-a.lastContactAt>=.045){const count=this.contact(a.plan.object);a.contacts+=count.jaw;a.contactSamples+=Number(count.jaw>0);a.lastContactAt=now;a.currentContacts=count.robot;}
    if(a.phase<0){
      if(!a.entrySent&&now>=2.5){this.sim.queueKey('KeyV',a.request_id,a.action);a.entrySent=true;}
      if(this.sim.fsm.mode()!=='claw_left'){if(now-a.started>8)this.abort('The native support controller did not enter the task mode.','failed');return null;}
      a.supportAt??=now;
      if(now-a.supportAt<(c.claw_settle_s??3))return null;
      this.nextStage();
    }
    if(!this.active)return null;
    if(!a.returning&&this.sim.fsm.mode()!=='claw_left'){this.abort('The support controller left the object task.','interrupted');return null;}
    const stage=a.plan.stages[a.phase],elapsed=now-a.stageAt;
    if(stage&&elapsed>=(stage.native_key_hold_s??stage.duration_s)&&a.heldKeys?.length){
      for(const code of a.heldKeys)this.sim.pending.push({code,down:false,at:now,requestId:a.request_id,action:a.action});
      a.heldKeys=[];
    }
    if(!stage){
      if(this.sim.fsm.mode()!=='locomotion'){
        a.stableSince=null;a.returnAt=null;
        if(now-a.stageAt>8)this.finish('failed','The controller did not return to a settled stance.',object);
        return null;
      }
      a.returnAt??=now;
      const goal=c.objects[a.plan.object],target=goal.target_xy;
      const tol=a.plan.target_tolerance_m??.018;
      const displacement=distance(object.position_m,a.initial[a.plan.object].position_m);
      const hand=a.plan.hand_xy;
      const closer=!hand||Math.hypot(a.initial[a.plan.object].position_m[0]-hand[0],a.initial[a.plan.object].position_m[1]-hand[1])-Math.hypot(object.position_m[0]-hand[0],object.position_m[1]-hand[1])>=(a.plan.minimum_hand_approach_m??.03);
      const box=object.bounds_m;
      const footprint=box.min.every(finite)&&box.max.every(finite)&&object.target_contained;
      const placed=now-a.returnAt>=2&&footprint&&Math.hypot(object.position_m[0]-target[0],object.position_m[1]-target[1])<=tol
        &&(a.plan.upright_required===false||object.tilt_deg<12)&&object.linear_speed_m_s<.025&&object.angular_speed_rad_s<.4
        &&Math.abs(object.position_m[2]-goal.start_position_m[2])<.012&&a.currentContacts===0
        &&displacement>=(a.plan.minimum_displacement_m??.05)&&closer&&a.contactSamples>=2;
      if(placed){a.stableSince??=now;if(now-a.stableSince>=.75){this.finish('completed',a.action==='cup'?'Your empty cup is on the coaster and released.':'The desk item is in its tray and released.',object);return null;}}
      else a.stableSince=null;
      if(now-a.stageAt>8){this.finish('failed','The object did not settle released inside its target. Please start a fresh scene.',object);return null;}
      return null;
    }
    const t=Math.max(0,Math.min(1,elapsed/(stage.duration_s*.7))),mix=t*t*(3-2*t);
    const targets=stage.joint_targets.map((q,i)=>a.from[i]+(q-a.from[i])*mix);a.lastTargets=targets;
    if(elapsed>=stage.duration_s)this.nextStage();
    return targets;
  }
  nextStage(){
    const a=this.active;if(!a)return;a.phase++;a.stageAt=this.sim.data.time;
    a.from=a.lastTargets?Array.from(a.lastTargets):this.config.wire_indices.map(i=>this.sim.data.qpos[this.sim.config.qadr[i]]);
    const stage=a.plan.stages[a.phase];
    const keys=stage?.native_keys??[];
    for(const code of keys)a.ownedKeys.add(code);
    for(const code of a.heldKeys??[])if(!keys.includes(code))this.sim.pending.push({code,down:false,at:this.sim.data.time,requestId:a.request_id,action:a.action});
    for(const code of keys)if(!(a.heldKeys??[]).includes(code))this.sim.pending.push({code,down:true,at:this.sim.data.time,requestId:a.request_id,action:a.action});
    a.heldKeys=keys.slice();
    if(stage)this.sim.emit('skill_progress',stage.message??stage.name.replaceAll('_',' '),{request_id:a.request_id,action:a.action,phase:stage.name});
    else {
      a.returning=true;
      this.sim.queueKey('KeyV',a.request_id,a.action);
      this.sim.emit('skill_progress','Returning to a quiet stance and checking the released object.',{request_id:a.request_id,action:a.action,phase:'verify_return_and_placement'});
    }
  }
}
