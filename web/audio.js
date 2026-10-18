/* Optional local-only companion audio. No microphone or remote TTS requests. */
export class CompanionAudio {
  constructor(onStatus=()=>{}) {
    this.onStatus=onStatus;this.enabled=false;this.context=null;this.nodes=new Set();this.generation=0;this.disposed=false;this.enabling=false;
  }
  voice() {
    try{return window.speechSynthesis?.getVoices().find(v=>v.localService===true&&/^en(?:-|$)/i.test(v.lang))??null;}catch(_){return null;}
  }
  async enable(enabled) {
    if(this.disposed)return false;
    this.stop();this.enabled=Boolean(enabled);const generation=this.generation;
    if(!this.enabled){this.onStatus('Sound is off. Messages remain on screen.');return false;}
    this.enabling=true;
    try {
      const Audio=window.AudioContext||window.webkitAudioContext;
      if(Audio&&!this.context)this.context=new Audio();
      if(this.context?.state==='suspended')await this.context.resume();
      if(this.disposed||generation!==this.generation||!this.enabled)return false;
      this.enabling=false;
      const voice=this.voice(),sounds=this.context?.state==='running';
      if(!voice&&!sounds){this.enabled=false;this.onStatus('This device has no local audio available. Messages remain on screen.');return false;}
      this.onStatus(voice?(sounds?'Quiet sounds and a local device voice are on.':'A local device voice is on. Chimes are unavailable.'):'Quiet sounds are on. No local English voice is available on this device.');
      this.say('Hello. I’m Mizu.', 'hello');return true;
    } catch(_) {
      if(this.disposed||generation!==this.generation)return false;
      this.enabling=false;this.enabled=false;this.stop();this.onStatus('Sound could not start. You can follow every message on screen.');return false;
    }
  }
  say(text,kind='notice') {
    if(!this.enabled||this.enabling||this.disposed||document.hidden)return;
    this.stop();
    const c=this.context;
    if(c?.state==='running') {
      try {
        const start=c.currentTime;
        for(const [i,hz] of (kind==='hello'?[523.25,659.25]:kind==='complete'?[523.25,783.99]:[440]).entries()) {
          const osc=c.createOscillator(),gain=c.createGain(),at=start+i*.14;
          osc.type='sine';osc.frequency.value=hz;gain.gain.setValueAtTime(0,at);
          gain.gain.linearRampToValueAtTime(.035,at+.025);gain.gain.exponentialRampToValueAtTime(.0001,at+.22);
          osc.connect(gain);gain.connect(c.destination);this.nodes.add(osc);
          osc.onended=()=>{this.nodes.delete(osc);osc.disconnect();gain.disconnect();};osc.start(at);osc.stop(at+.24);
        }
      }catch(_){this.onStatus('Audio is unavailable. Messages remain on screen.');}
    }
    const voice=this.voice();
    if(voice&&typeof window.SpeechSynthesisUtterance==='function') {
      try {
        // Never fall back to the browser default: it may be a remote service.
        const utterance=new window.SpeechSynthesisUtterance(String(text).slice(0,180));
        utterance.voice=voice;utterance.lang=voice.lang;utterance.rate=.95;utterance.pitch=1.05;utterance.volume=.55;
        const generation=this.generation;
        utterance.onerror=()=>{if(!this.disposed&&this.enabled&&generation===this.generation)this.onStatus('The local voice is unavailable. Messages remain on screen.');};
        window.speechSynthesis.speak(utterance);
      }catch(_){this.onStatus('The local voice is unavailable. Messages remain on screen.');}
    }
  }
  stop() {
    this.generation++;
    if(this.enabling){this.enabling=false;this.enabled=false;}
    for(const node of this.nodes){try{node.stop();node.disconnect();}catch(_){}}
    this.nodes.clear();try{window.speechSynthesis?.cancel();}catch(_){}
  }
  dispose(){if(this.disposed)return;this.stop();this.enabled=false;this.disposed=true;try{this.context?.close()?.catch(()=>{});}catch(_){}this.context=null;}
}
