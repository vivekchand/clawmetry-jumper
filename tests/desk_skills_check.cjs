const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const src=fs.readFileSync('web/manipulation.js','utf8').replace('export class DeskSkills','class DeskSkills')+'\nthis.DeskSkills=DeskSkills;';const scope={};vm.runInNewContext(src,scope);
function fixture(){
 const events=[],pending=[];let released=0;
 const object={body_id:0,dof_adr:0,geom_ids:[0],start_position_m:[0,0,.05],target_xy:[0,-.06],local_aabb:{0:[0,0,0,.01,.01,.01]},target_shape:'circle',target_radius_m:.04};
 const config={schema:'mizu_contact_skills/1',controller_kind:'scripted',objects:{empty_cup:object},joint_names:['a','b','c','d','e'],wire_indices:[0,1,2,3,4],claw_settle_s:2,jaw_geom_ids:[20],plans:{cup:{qualified:true,object:'empty_cup',stages:[{name:'slide',duration_s:.1,joint_targets:[0,0,0,0,0]}],minimum_displacement_m:.05,target_tolerance_m:.01,hand_xy:[0,-.4]}}};
 const sim={pending,data:{time:0,qpos:new Float64Array(5),xpos:new Float64Array([0,0,.05]),xmat:new Float64Array([1,0,0,0,1,0,0,0,1]),qvel:new Float64Array(6)},config:{qadr:[0,1,2,3,4]},fsm:{mode:()=> 'claw_left'},observationUntil:0,queueKey:(code,id,action)=>{sim.pending.push({code,requestId:id,action,down:true});if(code==='KeyV')sim.fsm.mode=()=> 'locomotion';},emit:(kind,message,data)=>events.push({kind,message,...data}),snapshot:()=>({margin_m:.3,tilt_deg:0,finite:true})};
 Object.defineProperty(sim.data,'geom_xpos',{get:()=>sim.data.xpos});Object.defineProperty(sim.data,'geom_xmat',{get:()=>sim.data.xmat});
 let touching=false;
 Object.defineProperty(sim.data,'contact',{configurable:true,get:()=>({size:()=>touching?1:0,get:()=>({geom1:0,geom2:20,dist:0,delete(){released++;}}),delete(){released++;}})});
 const skills=new scope.DeskSkills(sim,config);
 return {skills,sim,events,config,touch:v=>touching=v,released:()=>released};
}
let f=fixture();f.config.plans.cup.qualified=false;assert.match(f.skills.reason('cup'),/qualified/);
f=fixture();f.sim.data.xpos[0]=.03;assert.match(f.skills.reason('cup'),/moved/);
f=fixture();assert.equal(f.skills.start('cup','a').allowed,true);f.sim.data.time=2;f.skills.targets();f.sim.observationUntil=4;assert.equal(f.skills.targets(),null);assert.equal(f.skills.lastResult.outcome,'unknown');assert.equal(f.skills.active,null);
f=fixture();f.skills.start('cup','b');for(const t of [2,2.2,3,5,11]){f.sim.data.time=t;f.skills.targets();}assert.equal(f.skills.lastResult.outcome,'failed','time alone never proves placement');
f=fixture();f.skills.start('cup','c');f.sim.data.time=2;f.skills.targets();f.sim.data.xpos[1]=-.06;for(const t of [2.2,3,5,11]){f.sim.data.time=t;f.skills.targets();}assert.equal(f.skills.lastResult.outcome,'failed','a displaced object without observed robot contact is not success');
f=fixture();f.skills.start('cup','d');f.touch(true);for(const t of [2,2.06]){f.sim.data.time=t;f.skills.targets();}f.sim.data.xpos[1]=-.06;f.sim.data.time=2.2;f.skills.targets();f.touch(false);for(const t of [2.3,2.4,4.4,5.2]){f.sim.data.time=t;f.skills.targets();}assert.equal(f.skills.lastResult.outcome,'completed');assert.ok(f.released()>2,'both contact vectors and contact entries are released');
// Center-only placement and jaw-only release must never earn success.
for(const problem of ['overhang','other_robot_contact']){
 f=fixture();if(problem==='overhang')f.config.objects.empty_cup.local_aabb[0]=[0,0,0,.03,.03,.01];
 f.skills.start('cup',problem);f.touch(true);for(const t of [2,2.06]){f.sim.data.time=t;f.skills.targets();}
 f.sim.data.xpos[1]=-.06;f.sim.data.time=2.2;f.skills.targets();f.touch(false);
 if(problem==='other_robot_contact'){
  f.sim.config.robot_collision_geoms=[20,30];
  Object.defineProperty(f.sim.data,'contact',{configurable:true,get:()=>({size:()=>1,get:()=>({geom1:0,geom2:30,dist:0,delete(){}}),delete(){}})});
 }
 for(const t of [2.3,3.2,11]){f.sim.data.time=t;f.skills.targets();}
 assert.equal(f.skills.lastResult.outcome,'failed',problem);
}
f=fixture();f.sim.fsm.mode=()=> 'locomotion';f.skills.start('cup','cancel');f.sim.data.time=2.5;f.skills.targets();assert.ok(f.sim.pending.some(e=>e.down));f.skills.abort();assert.ok(!f.sim.pending.some(e=>e.down),'cancellation removes a pending native entry');assert.equal(f.skills.targets(),null);
// Placement cannot succeed before native exit; an exit disturbance fails it.
f=fixture();f.skills.start('cup','exit');f.touch(true);for(const t of [2,2.06]){f.sim.data.time=t;f.skills.targets();}
f.sim.data.xpos[1]=-.06;f.sim.data.time=2.2;f.skills.targets();f.touch(false);
assert.equal(f.skills.lastResult,null,'native return must precede completion');
f.sim.data.xmat[8]=0;f.sim.data.time=2.3;f.skills.targets();assert.equal(f.skills.lastResult.outcome,'failed','return-motion disturbance invalidates placement');
// Walking edges expire inside a stage, not only when its arm motion ends.
f=fixture();f.config.plans.cup.stages[0]={name:'slide',duration_s:5,joint_targets:[0,0,0,0,0],native_keys:['KeyW'],native_key_hold_s:.8};
f.skills.start('cup','walk');f.sim.data.time=2;f.skills.targets();assert.ok(f.sim.pending.some(e=>e.code==='KeyW'&&e.down));
f.sim.data.time=2.81;f.skills.targets();assert.ok(f.sim.pending.some(e=>e.code==='KeyW'&&!e.down));assert.equal(f.skills.active.phase,0);
f.skills.abort();assert.ok(f.sim.pending.some(e=>e.code==='KeyW'&&!e.down),'cancel preserves a release whose first queued edge was not consumed');
// A sphere's radius is orientation-invariant; a tray can have a containment
// center different from its semantic delivery target.
f=fixture();f.config.objects.empty_cup.geometry={0:{type:2,size:[.01,0,0]}};
f.config.objects.empty_cup.target_radius_m=.011;f.sim.data.xpos[1]=-.06;
f.sim.data.xmat.set([Math.SQRT1_2,-Math.SQRT1_2,0,Math.SQRT1_2,Math.SQRT1_2,0,0,0,1]);
assert.equal(f.skills.objects().empty_cup.target_contained,true);
assert.ok(Math.abs(f.skills.objects().empty_cup.bounds_m.max[0]-.01)<1e-10);
f=fixture();Object.assign(f.config.objects.empty_cup,{target_shape:'box',target_center_xy:[-.04,-.06],target_half_size_m:[.02,.02]});
f.sim.data.xpos.set([-.04,-.06,.05]);assert.equal(f.skills.objects().empty_cup.target_contained,true);
f.sim.data.xpos[0]=-.01;assert.equal(f.skills.objects().empty_cup.target_contained,false);
console.log('Task gates, unknown/failed outcomes, measured contact/release result, cancellation and contact disposal pass.');
