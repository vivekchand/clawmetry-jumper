"""Read-only local Flask view, with no controller or action HTTP endpoints."""
from __future__ import annotations

from contextlib import contextmanager
import logging
from pathlib import Path

import duckdb
from flask import Blueprint, current_app, jsonify, request

from .evidence import EvidenceStore, validate_limit, validate_run_id

_LOG = logging.getLogger(__name__)
_UNAVAILABLE = (
    "Local simulation evidence is unavailable. Run the simulator and this page in the same "
    "process with a shared EvidenceStore, or open a completed database after its collector closes."
)


def create_blueprint(store: EvidenceStore | None = None, *, db_path: str | Path | None = None) -> Blueprint:
    bp = Blueprint("clawmetry_jumper", __name__)

    @contextmanager
    def evidence():
        shared = store if store is not None else current_app.config.get("JUMPER_EVIDENCE_STORE")
        if shared is not None:
            if not isinstance(shared, EvidenceStore):
                raise RuntimeError("A shared EvidenceStore object is required")
            yield shared
        else:
            path = db_path or current_app.config.get("JUMPER_EVIDENCE_DB")
            if not path or not isinstance(path, (str, Path)):
                raise RuntimeError("No local collector configured")
            # Read completed stores only. Do not create files or contend with a
            # collector in another process, and do not hold a read lock afterward.
            with EvidenceStore(path, read_only=True) as completed:
                yield completed

    @bp.get("/jumper")
    def jumper_page():
        return _PAGE, 200, {"Cache-Control": "no-store"}

    @bp.get("/api/jumper/evidence")
    def jumper_evidence():
        try:
            raw_limit = request.args.get("limit", "200")
            if not raw_limit.isascii() or not raw_limit.isdigit():
                raise ValueError("Limit must be an integer from 1 to 1000")
            limit = validate_limit(int(raw_limit))
            run_id = request.args.get("run_id")
            if run_id is not None:
                validate_run_id(run_id)
        except ValueError as error:
            return jsonify(error=str(error)), 400, {"Cache-Control": "no-store"}
        try:
            with evidence() as local:
                result = {"local_simulation": True, "runs": local.runs(),
                          "events": local.events(run_id=run_id, limit=limit), "limit": limit,
                          "read_only_view": True}
            return jsonify(result), 200, {"Cache-Control": "no-store"}
        except (duckdb.Error, OSError, RuntimeError, ValueError):
            # Paths and database exception text can expose local details.
            _LOG.warning("Jumper evidence is unavailable; check the local collector connection")
            return jsonify(error=_UNAVAILABLE, local_simulation=True), 503, {"Cache-Control": "no-store"}

    return bp


def register_all(app) -> None:
    """Public standalone extension entry point; explicit Flask app is required."""
    if "clawmetry_jumper" not in app.blueprints:
        app.register_blueprint(create_blueprint())


_PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jumper · Local simulation evidence</title>
<style>
:root{color-scheme:dark;font:16px/1.55 system-ui,sans-serif;background:#101712;color:#edf4ed}*{box-sizing:border-box}
body{margin:0}main{max-width:1120px;margin:auto;padding:32px 24px 64px}header{display:flex;justify-content:space-between;gap:20px;align-items:center;border-bottom:1px solid #344b3b;padding-bottom:24px}
.brand{font-weight:750;letter-spacing:.03em}.badge{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#b7e7c0;border:1px solid #497653;border-radius:30px;padding:6px 12px}
.hero{padding:44px 0 28px}h1{font-size:clamp(30px,5vw,52px);line-height:1.12;letter-spacing:-.04em;margin:8px 0 18px}p{color:#b4c6b8;max-width:750px}label{display:block;font-size:13px;color:#b4c6b8;margin-bottom:8px}select{font:inherit;color:inherit;background:#1b2a20;border:1px solid #4c6554;border-radius:9px;padding:10px;max-width:100%;min-width:220px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:24px 0}.card{border:1px solid #344b3b;border-radius:14px;padding:20px;background:#16211a}.card strong{font-size:24px;display:block}.muted,.hint{font-size:13px;color:#afc2b3}.timeline{display:grid;gap:10px;margin-top:18px}.event{border:1px solid #344b3b;border-radius:12px;padding:16px 18px;background:#16211a}.event-head{display:flex;gap:12px;justify-content:space-between;flex-wrap:wrap}.kind{font-weight:700;text-transform:capitalize}.time{color:#9cb7a3;font-size:13px}.payload{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 ui-monospace,monospace;margin:12px 0 0;color:#d4e3d8}.error{color:#f2c49c}.notice{border-left:3px solid #8dc69b;padding-left:16px}.section-title{margin-top:34px}footer{margin-top:32px;color:#9bb0a1;font-size:13px}
@media(max-width:600px){main{padding:22px 16px}header{align-items:flex-start}.cards{grid-template-columns:1fr}.hero{padding-top:30px}.badge{max-width:160px;text-align:center}.card{padding:15px}}
</style></head><body><main>
<header><span class="brand">Jumper / ClawMetry</span><span class="badge">Local simulation</span></header>
<section class="hero"><span class="hint">A healthier desk, one small reminder at a time</span><h1>A companion with clear boundaries.</h1>
<p>Review reminders, permission decisions and measured simulator outcomes. Follow each request through the controller receipt and the evidence that comes after it.</p>
<p class="notice">This page observes recorded local evidence. A permission decision or controller receipt does not prove a measured outcome. Missing observations leave the outcome unknown. Physical hardware, water handling and tidying are not validated.</p></section>
<label for="run">Simulation run</label><select id="run"><option value="">Latest evidence across runs</option></select>
<div class="cards"><div class="card"><span class="muted">Recorded runs</span><strong id="run-count">0</strong></div><div class="card"><span class="muted">Loaded events</span><strong id="event-count">0</strong></div><div class="card"><span class="muted">View</span><strong>Observation only</strong></div></div>
<h2 class="section-title">Evidence timeline</h2><p id="status" role="status" aria-live="polite">Connecting to the local collector…</p><div id="timeline" class="timeline"></div>
<footer>Local prototype · Simulator evidence only · No action controls are exposed by this page.</footer>
</main><script>
(()=>{'use strict';const run=document.getElementById('run'),timeline=document.getElementById('timeline'),status=document.getElementById('status');let busy=false;
async function load(){if(busy||document.hidden)return;busy=true;try{const query=new URLSearchParams({limit:'200'});if(run.value)query.set('run_id',run.value);const response=await fetch('/api/jumper/evidence?'+query,{cache:'no-store'});const data=await response.json();if(!response.ok)throw new Error(data.error||'Local evidence is unavailable.');const selected=run.value;run.replaceChildren(new Option('Latest evidence across runs',''));for(const item of data.runs)run.add(new Option(item.run_id+' · '+item.event_count+' events',item.run_id));if(selected&&!data.runs.some(item=>item.run_id===selected))run.add(new Option(selected,selected));run.value=selected;document.getElementById('run-count').textContent=data.runs.length;document.getElementById('event-count').textContent=data.events.length;timeline.replaceChildren();for(const event of data.events){const card=document.createElement('article');card.className='event';const head=document.createElement('div');head.className='event-head';const kind=document.createElement('span');kind.className='kind';kind.textContent=event.kind;const time=document.createElement('span');time.className='time';time.textContent=Number(event.sim_time_s).toFixed(3)+' s simulation · event '+event.event_id;head.append(kind,time);const payload=document.createElement('pre');payload.className='payload';payload.textContent=JSON.stringify(event.payload,null,2);const source=document.createElement('div');source.className='hint';source.textContent=event.run_id;card.append(head,source,payload);timeline.append(card);}status.className='';status.textContent=data.events.length?'Latest '+data.events.length+' persisted events, in capture order.':'No events recorded yet. Start the local simulator collector.';}catch(error){status.className='error';status.textContent=error.message;timeline.replaceChildren();document.getElementById('event-count').textContent='Unavailable';}finally{busy=false;}}
run.addEventListener('change',load);document.addEventListener('visibilitychange',()=>{if(!document.hidden)load();});setInterval(load,3000);load();})();
</script></body></html>'''
