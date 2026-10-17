import * as THREE from 'three';
import {OrbitControls} from './vendor/three/OrbitControls.js';
const decode=(text,Type)=>{const raw=atob(text),bytes=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)bytes[i]=raw.charCodeAt(i);return new Type(bytes.buffer);};

export class DeskRenderer {
  constructor(container, simulation, isRunning=()=>true) {
    this.container=container;this.sim=simulation;
    this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'low-power'});
    this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));this.renderer.shadowMap.enabled=true;
    this.renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    this.renderer.setClearColor(0xe8ecdf);this.renderer.outputColorSpace=THREE.SRGBColorSpace;
    this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1;
    container.append(this.renderer.domElement);
    this.scene=new THREE.Scene();this.scene.background=new THREE.Color(0xe8ecdf);
    this.camera=new THREE.PerspectiveCamera(42,1,.02,30);this.camera.up.set(0,0,1);
    this.camera.position.set(2.1,-2.7,1.8);
    this.controls=new OrbitControls(this.camera,this.renderer.domElement);
    this.controls.target.set(-.04,-.22,.02);this.controls.minDistance=.6;this.controls.maxDistance=7;
    this.controls.maxPolarAngle=Math.PI*.48;this.controls.update();
    const ambient=new THREE.HemisphereLight(0xfff9e8,0x7a8b74,2.1);ambient.position.set(0,0,3);this.scene.add(ambient);
    const sun=new THREE.DirectionalLight(0xfff7e7,2.5);sun.position.set(1,-2,4);sun.castShadow=true;
    sun.shadow.mapSize.set(2048,2048);sun.shadow.camera.left=-2;sun.shadow.camera.right=2;
    sun.shadow.camera.top=2;sun.shadow.camera.bottom=-2;sun.shadow.bias=-.0004;this.scene.add(sun);
    this.meshes=[];this.geometries=new Map();
    for(const g of simulation.config.render_geoms){
      const geometry=this.geometry(g);if(!geometry)continue;
      const rgba=g.rgba;
      const material=new THREE.MeshStandardMaterial({color:new THREE.Color().setRGB(rgba[0],rgba[1],rgba[2],THREE.LinearSRGBColorSpace),roughness:.8,metalness:.03,transparent:rgba[3]<1,opacity:rgba[3]});
      const mesh=new THREE.Mesh(geometry,material);mesh.castShadow=g.type!==0;mesh.receiveShadow=true;mesh.matrixAutoUpdate=false;
      this.scene.add(mesh);this.meshes.push({id:g.id,mesh});
    }
    this.isRunning=isRunning;this.controls.addEventListener('change',()=>{if(!this.isRunning())this.draw();});
    this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(container);this.resize();this.draw();
  }

  geometry(g){
    const s=g.size;
    if(g.type===7){
      if(this.geometries.has(g.mesh))return this.geometries.get(g.mesh);
      const data=this.sim.config.render_meshes[g.mesh], geom=new THREE.BufferGeometry();
      geom.setAttribute('position',new THREE.BufferAttribute(decode(data.vertices_f32,Float32Array),3));
      geom.setIndex(new THREE.BufferAttribute(decode(data.faces_u32,Uint32Array),1));geom.computeVertexNormals();
      this.geometries.set(g.mesh,geom);return geom;
    }
    if(g.type===0)return new THREE.PlaneGeometry(10,10);
    if(g.type===2)return new THREE.SphereGeometry(s[0],20,14);
    if(g.type===3){const geom=new THREE.CapsuleGeometry(s[0],2*s[1],6,14);geom.rotateX(Math.PI/2);return geom;}
    if(g.type===4){const geom=new THREE.SphereGeometry(1,20,14);geom.scale(...s);return geom;}
    if(g.type===5){const geom=new THREE.CylinderGeometry(s[0],s[0],2*s[1],24);geom.rotateX(Math.PI/2);return geom;}
    if(g.type===6)return new THREE.BoxGeometry(2*s[0],2*s[1],2*s[2]);
    return null;
  }
  resize(){if(this.disposed)return;const w=this.container.clientWidth,h=this.container.clientHeight;if(!w||!h)return;this.camera.aspect=w/h;this.camera.updateProjectionMatrix();this.renderer.setSize(w,h,false);this.draw();}
  draw(){
    if(this.disposed||this.sim.disposed)return;
    const d=this.sim.data;
    for(const {id,mesh} of this.meshes){const p=d.geom_xpos.subarray(id*3,id*3+3),r=d.geom_xmat.subarray(id*9,id*9+9);mesh.matrix.set(r[0],r[1],r[2],p[0],r[3],r[4],r[5],p[1],r[6],r[7],r[8],p[2],0,0,0,1);mesh.matrixWorldNeedsUpdate=true;}
    this.renderer.render(this.scene,this.camera);
  }
  dispose(){
    if(this.disposed)return;this.disposed=true;
    this.resizeObserver.disconnect();this.controls.dispose();
    const geometries=new Set(),materials=new Set();
    for(const {mesh} of this.meshes){geometries.add(mesh.geometry);for(const m of (Array.isArray(mesh.material)?mesh.material:[mesh.material]))materials.add(m);this.scene.remove(mesh);}
    for(const geometry of geometries)geometry.dispose();for(const material of materials)material.dispose();
    this.renderer.dispose();this.renderer.forceContextLoss();this.renderer.domElement.remove();this.meshes=[];
  }
}
