"""Actual isolated Chromium acceptance; requires Playwright, no user Chrome profile."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

out = Path(os.environ.get('JUMPER_OUT', Path(__file__).resolve().parents[1] / 'test-results'))
out.mkdir(exist_ok=True)
report = {'cases': {}, 'errors': []}
url = os.environ.get('JUMPER_URL', 'http://127.0.0.1:8957/')
origin = urlsplit(url)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1100})
    page.on('pageerror', lambda e: report['errors'].append(str(e)))
    requested=[]
    page.on('request',lambda r:requested.append(r.url))
    page.set_default_timeout(120000)
    page.goto(url, wait_until='networkidle')
    # No WASM or asset downloads before explicit opt-in.
    assert page.evaluate('typeof window.jumperDemo') == 'undefined'
    assert not any('/assets/' in u or '/vendor/' in u or u.endswith('.wasm') for u in requested)
    page.get_by_role('button', name='Start simulation').click()
    page.wait_for_function('!!window.jumperDemo', timeout=120000)
    page.evaluate('jumperDemo.pause()')
    report['qualification'] = page.evaluate('({controller:jumperDemo.engine.reference,inference:jumperDemo.engine.inferenceReference,counts:jumperDemo.engine.config.counts})')
    print('QUALIFIED', report['qualification'], flush=True)
    def advance(n):
        return page.evaluate('(n)=>jumperDemo.advance(n)', n)
    def fresh():
        page.evaluate('jumperDemo.engine.reset()')
        return advance(500)
    fresh()
    report['cases']['settle'] = page.evaluate('jumperDemo.snapshot()')
    for action in ['wave', 'bow']:
        fresh()
        result = page.evaluate('(a)=>jumperDemo.request(a)', action)
        assert result['allowed'], result
        mid = advance(500)
        page.screenshot(path=str(out/f'{action}.png'), full_page=True)
        final = advance(2000)
        evidence = page.evaluate('jumperDemo.evidence()')
        modes = [e.get('to') for e in evidence['events'] if e['kind']=='controller_mode' and e['episode']==evidence['current_episode']]
        outcome=next(e for e in evidence['events'] if e['kind']=='action_outcome' and e.get('request_id')==result['request_id'])
        assert outcome['outcome']=='returned_within_observed_boundary' and outcome['feed_complete']
        assert ('gesture_hello' if action=='wave' else 'gesture_bow') in modes, modes
        assert final['finite']
        report['cases'][action] = {'request':result,'mid':mid,'final':final,'minimum_observed_margin_m':evidence['minimum_observed_margin_m'],'modes':modes}
        print(action, report['cases'][action], flush=True)
    fresh()
    for action in ['jump', 'cup']:
        result = page.evaluate('(a)=>jumperDemo.request(a)', action)
        assert not result['allowed']
        advance(200)
        assert page.evaluate('jumperDemo.engine.fsm.mode()') == 'locomotion'
        report['cases'][action] = result
    fresh()
    request=page.evaluate("jumperDemo.request('wave')")
    advance(1200)
    page.evaluate("jumperDemo.experiment('stale')")
    advance(800)
    outcome=page.evaluate('(id)=>jumperDemo.engine.events.find(e=>e.kind==="action_outcome"&&e.request_id===id)',request['request_id'])
    assert outcome['outcome']=='unknown' and not outcome['feed_complete']
    report['cases']['gesture_observation_loss']=outcome
    fresh()
    before = page.evaluate('jumperDemo.snapshot()')
    page.evaluate("jumperDemo.experiment('stale')")
    advance(200)
    denied = page.evaluate("jumperDemo.request('wave')")
    assert not denied['allowed']
    assert page.locator('#observation').inner_text().startswith('Unavailable')
    after = page.evaluate('jumperDemo.snapshot()')
    assert after['sim_time_s'] > before['sim_time_s'] + .99
    page.screenshot(path=str(out/'stale.png'), full_page=True)
    advance(500)
    assert page.evaluate('jumperDemo.engine.observationUntil') == 0
    report['cases']['stale']={'before':before,'while_unavailable':after,'denied':denied}
    for action in ['lift','drift']:
        fresh()
        page.evaluate('(a)=>jumperDemo.experiment(a)',action)
        mid = advance(60)
        final = advance(400)
        assert page.evaluate('jumperDemo.engine.force') is None
        assert page.evaluate('Array.from(jumperDemo.engine.data.xfrc_applied).every(x=>x===0)')
        evidence = page.evaluate('jumperDemo.evidence()')
        alerts = [e['alert'] for e in evidence['events'] if e['kind']=='measured_alert' and e['episode']==evidence['current_episode']]
        assert final['finite']
        assert ('lift' if action=='lift' else 'breach') in alerts, {"mid":mid,"final":final,"alerts":alerts}
        report['cases'][action]={'mid':mid,'final':final,'alerts':alerts,'force_removed':True}
        page.screenshot(path=str(out/f'{action}.png'),full_page=True)
        print(action,report['cases'][action],flush=True)
    fresh()
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(out/'mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    # A paused playground stays idle, but camera changes can still render.
    page.evaluate('''() => {
      jumperDemo.pause();window.drawCount=0;
      const draw=jumperDemo.view.draw.bind(jumperDemo.view);
      jumperDemo.view.draw=()=>{window.drawCount++;return draw();};
    }''')
    page.wait_for_timeout(100)
    before_draws=page.evaluate('window.drawCount')
    page.wait_for_timeout(200)
    assert page.evaluate('window.drawCount')==before_draws
    page.evaluate("jumperDemo.view.controls.dispatchEvent({type:'change'})")
    assert page.evaluate('window.drawCount')==before_draws+1
    assert 'Scene ' in page.locator('#timeline time').first.inner_text()
    assert page.get_by_text('Controller reference matched',exact=True).count()<=1
    # Start a real asynchronous control step, retire the page, and verify
    # that its eventual inference cannot resume a freed controller/model.
    lifecycle=page.evaluate('''async () => {
      const old=jumperDemo,step=old.engine.step().catch(e=>e.message);
      const tickAtHide=old.engine.tick;
      window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}));
      const pendingResult=await step;await old.engine.disposal;
      const result={disposed:old.engine.disposed,modelReleased:old.engine.model===null,
        controllerReleased:old.engine.fsm===null,vfsReleased:old.engine.vfs===null,
        meshesReleased:old.view.meshes.length===0,canvasRemoved:!document.querySelector('#viewport canvas'),
        noFurtherStep:old.engine.tick===tickAtHide,apiRetired:!window.jumperDemo,pendingResult};
      window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}));
      result.restartVisible=!document.querySelector('#start-overlay').hidden;
      result.restartEnabled=!document.querySelector('#start').disabled;
      return result;
    }''')
    assert all(lifecycle[k] for k in ['disposed','modelReleased','controllerReleased','vfsReleased','meshesReleased','canvasRemoved','noFurtherStep','apiRetired','restartVisible','restartEnabled']),lifecycle
    report['cases']['lifecycle']=lifecycle
    report['cases']['paused_render']={'idle_redraws':0,'camera_change_redraws':1}
    assert all((urlsplit(u).scheme, urlsplit(u).netloc) == (origin.scheme, origin.netloc) for u in requested), requested
    report['network_scope']='Static assets only; no camera, microphone, backend API or hardware connection'
    report['passed']=not report['errors']
    browser.close()
(out/'browser-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
