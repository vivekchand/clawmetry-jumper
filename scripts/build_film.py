#!/usr/bin/env python3
"""Build a review film from measured simulator footage, without paid services."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from clawmetry_jumper.evidence import EvidenceStore
from clawmetry.physical_ai import DeskMonitor, JumperObserver
from clawmetry_jumper.simulator import JumperSimulator

W, H, FPS, DURATION = 1920, 1080, 30, 84
CREAM, INK, MUTED = '#f8f7ef', '#193d33', '#5f746b'
SAGE, PALE, CORAL = '#87ad98', '#e6eee3', '#d96f56'
FONT = '/System/Library/Fonts/SFNSRounded.ttf'
BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'

NARRATION = [
    (0.5, 6.8, 'Meet Mizu. A gentle desk companion, with ClawMetry keeping you informed.'),
    (7.3, 11.8, 'Cup delivery and tidying come later.'),
    (12.5, 21.0, 'A greeting is allowed. The official Jumper controller begins its wave.'),
    (22.0, 28.0, 'Permission, delivery, and what actually happens are recorded separately.'),
    (28.4, 34.2, 'A stretch reminder starts a bow. The simulation keeps running.'),
    (37.3, 46.0, 'A jump is outside the desk task. ClawMetry declines the request, and withholds that input.'),
    (47.5, 56.5, 'Away from your desk? Review the requests, decisions, and observed movements in your local history.'),
    (57.5, 66.5, 'Here, a separate test applies an upward force. ClawMetry records the measured lift and tilt.'),
    (67.4, 73.7, 'This recording shows local alerts. Phone delivery needs a configured notification channel.'),
    (74.5, 83.5, 'Explore ClawMetry for physical AI. Open source observation, with a clearer record and room to grow.'),
]
BRAND = None


def command(*args):
    subprocess.run([str(v) for v in args], check=True, stdout=subprocess.DEVNULL)


def font(size, bold=False):
    for candidate in (BOLD if bold else FONT, 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    raise RuntimeError('Install DejaVu Sans or supply --font and --bold-font paths for film rendering')


class FontCache(dict):
    def __missing__(self, key):
        face = font(*key)
        self[key] = face
        return face


# Resolve only while drawing. Even a fontless host can inspect --help.
FONTS = FontCache()


def label(draw, xy, text, size=28, fill=INK, bold=False, spacing=12):
    draw.multiline_text(xy, text, font=FONTS[size, bold], fill=fill, spacing=spacing)


def wrap(text, width, size=30, bold=False):
    words, lines, line = text.split(), [], ''
    f = FONTS[size, bold]
    for word in words:
        candidate = (line + ' ' + word).strip()
        if f.getlength(candidate) > width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return '\n'.join(lines)


def canvas(chapter):
    im = Image.new('RGB', (W, H), CREAM)
    d = ImageDraw.Draw(im)
    if BRAND is None:
        raise RuntimeError('An official ClawMetry brand asset is required')
    d.rounded_rectangle((48, 18, 316, 91), 13, fill=INK)
    im.paste(BRAND, (64, 29), BRAND)
    label(d, (1460, 38), 'MIZU / PHYSICAL AI', 24, MUTED)
    d.line((48, 104, 1872, 104), fill='#ccd8cb', width=2)
    label(d, (48, 1017), chapter.partition(' / ')[2] or chapter, 22, MUTED)
    label(d, (1600, 1017), 'SIMULATION', 20, MUTED)
    return im


def video_writer(path, width, height):
    return subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{width}x{height}', '-r', str(FPS),
        '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(path)], stdin=subprocess.PIPE)


def video_reader(path, seconds):
    return subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(path),
        '-t', str(seconds), '-vf', f'fps={FPS},scale=1280:720', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
        stdout=subprocess.PIPE)


def next_frame(reader):
    data = reader.stdout.read(1280 * 720 * 3)
    return Image.frombytes('RGB', (1280, 720), data) if len(data) == 1280 * 720 * 3 else None


def lift_test(upstream, scene, out):
    """A real force perturbation, with no pose writes after reset."""
    movie = out / 'scripted-lift-native.mp4'
    db = out / 'scripted-lift.duckdb'
    # Keep this run reproducible when rebuilding the film.
    if db.exists():
        db.unlink()
    simulator = JumperSimulator(upstream, scene_xml=scene)
    monitor = DeskMonitor()
    writer = video_writer(movie, 1280, 720)
    report = {'force_n': 28, 'force_interval_s': [2, 2.3], 'finite': True,
              'max_height_m': 0, 'max_tilt_deg': 0, 'min_table_margin_m': 1,
              'alerts': [], 'pose_overrides_after_reset': False,
              'engine': 'standalone native MuJoCo host with official imported scene',
              'phone_delivery_confirmed': False}
    with EvidenceStore(db) as store:
        observer = JumperObserver('mizu-film-lift', environment='simulation',
                                  monitor=DeskMonitor(), sample_interval_s=.1)
        observer.__enter__()
        try:
            writer.stdin.write(simulator.render().tobytes())
            frames = 1
            for i in range(1200):
                t = i * simulator.dt
                simulator.data.xfrc_applied[simulator._body, 2] = 28 if 2 <= t < 2.3 else 0
                observed = simulator.step()
                observer.observe(observed, now_s=observed['time_s'])
                report['finite'] &= observed['finite']
                report['max_height_m'] = max(report['max_height_m'], observed['position_m'][2])
                report['max_tilt_deg'] = max(report['max_tilt_deg'], observed['tilt_deg'])
                report['min_table_margin_m'] = min(report['min_table_margin_m'], observed['table_margin_m'])
                if i % 10 == 0:
                    store.append('film-scripted-lift', observed['time_s'], 'observation', observed)
                for alert in monitor.update(observed, observed['time_s']):
                    report['alerts'].append(alert)
                    store.append('film-scripted-lift', observed['time_s'], 'alert', alert)
                    store.append('film-scripted-lift', observed['time_s'], 'notification', {
                        'alert_type': alert['type'], 'status': 'not_configured',
                        'phone_delivery_confirmed': False, 'scope': 'demo_capture_only'})
                if observed['time_s'] + 1e-9 >= frames / FPS:
                    writer.stdin.write(simulator.render().tobytes())
                    frames += 1
            store.append('film-scripted-lift', observed['time_s'], 'outcome', report)
        finally:
            observer.__exit__(None, None, None)
            report['shared_observer'] = observer.status()
            writer.stdin.close()
            if writer.wait() != 0:
                raise RuntimeError('Lift video encoder failed')
            simulator.close()
    (out / 'scripted-lift.report.json').write_text(json.dumps(report, indent=2) + '\n')
    if not report['finite'] or not any(a['type'] == 'unexpected_lift' for a in report['alerts']):
        raise RuntimeError('The real lift test did not produce the required finite alert evidence')
    return movie, report


def aligned_captions(receipt, offset):
    """Use provider character times, grouped at word/sentence boundaries."""
    words, word, begin, finish = [], '', None, None
    for group in receipt.get('timestamps', []):
        chars = group.get('characters', [])
        starts = group.get('character_start_times_seconds', [])
        ends = group.get('character_end_times_seconds', [])
        if len(chars) != len(starts) or len(chars) != len(ends):
            raise RuntimeError('Premium narration has inconsistent alignment')
        for char, start, end in zip(chars, starts, ends):
            if char.isspace():
                if word:
                    words.append((word, begin, finish))
                    word, begin = '', None
            else:
                if begin is None:
                    begin = float(start)
                word += char
                finish = float(end)
    if word:
        words.append((word, begin, finish))
    if not words or any(b[1] < a[1] for a, b in zip(words, words[1:])):
        raise RuntimeError('Premium captions require monotonic speech alignment')
    cues, group = [], []
    def flush():
        if group:
            cues.append({'start': offset + group[0][1], 'end': offset + group[-1][2],
                         'text': ' '.join(w[0] for w in group)})
            group.clear()
    for entry in words:
        if group and (len(' '.join(w[0] for w in [*group, entry])) > 68 or entry[2] - group[0][1] > 4.5):
            flush()
        group.append(entry)
        if entry[0].endswith(('.', '!', '?')):
            flush()
    flush()
    return cues


def premium_audio(out, voice_dir):
    """Use explicitly generated premium clips; never fall back to system speech."""
    manifest = json.loads((voice_dir / 'manifest.json').read_text())
    if manifest.get('voice') != 'Rachel' or manifest.get('model') != 'fal-ai/elevenlabs/tts/eleven-v3':
        raise RuntimeError('Expected the approved premium neural voice manifest')
    clips, segments, captions = [], [], []
    for i, (start, end, text) in enumerate(NARRATION):
        path = voice_dir / f'voice-{i:02}.mp3'
        receipt = json.loads(path.with_suffix('.speech.json').read_text())
        expected = manifest['clips'][i]
        if expected.get('text') != text or expected.get('sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
            raise RuntimeError('Premium voice clip differs from its cached generation manifest')
        if receipt.get('text') != text or receipt.get('voice') != manifest['voice'] or receipt.get('model') != manifest['model']:
            raise RuntimeError('Premium voice clip does not match the authored narration')
        duration = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
            'format=duration', '-of', 'default=nw=1:nk=1', str(path)], text=True))
        if duration > end - start - .05:
            raise RuntimeError(f'Premium narration {i} needs a shorter script or a longer chapter')
        clips.append(path)
        captions.extend(aligned_captions(receipt, start))
        segments.append({'start': start, 'end': round(start + duration, 3), 'text': text,
                         'voice': 'ElevenLabs Eleven v3 Rachel via fal',
                         'listening_review': manifest.get('listening_review', 'pending')})
    args = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y']
    for clip in clips:
        args += ['-i', str(clip)]
    filters = ';'.join(f'[{i}:a]adelay={round(s["start"] * 1000)}|{round(s["start"] * 1000)}[a{i}]'
                       for i, s in enumerate(segments))
    filters += ';' + ''.join(f'[a{i}]' for i in range(len(clips))) + f'amix=inputs={len(clips)}:normalize=0,apad=whole_dur={DURATION},loudnorm=I=-16:TP=-1.5:LRA=11[a]'
    command(*args, '-filter_complex', filters, '-map', '[a]', '-t', DURATION, out / 'narration.wav')
    return segments, captions


def stamp(seconds):
    millis = round(seconds * 1000)
    return f'{millis//3600000:02}:{millis//60000%60:02}:{millis//1000%60:02},{millis%1000:03}'


def portrait_excerpt(root):
    """A 35-second portrait excerpt of the same unsped official recording."""
    out = root / 'artifacts/film'
    manifest = json.loads((out / 'film-manifest.json').read_text())
    source = Path(manifest['official_source_unsped'])
    times = manifest['shared_timeline_s']
    observations = [e['data'] for e in map(json.loads, (out / 'official-shared-journal.jsonl').read_text().splitlines())
                    if e['kind'] == 'observation']
    captions = [dict(c, start=c['start']-12, end=c['end']-12)
                for c in json.loads((out / 'captions.json').read_text()) if c['start'] >= 12 and c['end'] <= 47]
    brand = Image.open(out / 'brand/clawmetry-logo-horizontal-darkbg.png').convert('RGBA')
    brand = brand.crop(brand.getbbox())
    brand = brand.resize((300, round(300 * brand.height / brand.width)), Image.Resampling.LANCZOS)
    reader = video_reader(source, 35)
    writer = video_writer(out / 'portrait-silent.mp4', 1080, 1920)
    preview = None
    try:
        for index in range(35 * FPS):
            t = index / FPS
            picture = next_frame(reader)
            if picture is None:
                raise RuntimeError('Official source ended before the portrait excerpt')
            im = Image.new('RGB', (1080, 1920), CREAM)
            d = ImageDraw.Draw(im)
            d.rounded_rectangle((40, 30, 380, 132), 16, fill=INK)
            im.paste(brand, (60, 43), brand)
            label(d, (40, 200), 'Small tasks.\nClear boundaries.', 76, bold=True, spacing=16)
            im.paste(picture.resize((1000, 562), Image.Resampling.LANCZOS), (40, 440))
            if t < times['wave']:
                title, body = 'Ready to help', 'A wave and a bow are within this task.'
            elif t < times['hello_end']:
                title, body = 'Wave allowed', 'Input delivered. Native greeting observed.'
            elif t < times['bow']:
                title, body = 'Greeting completed', 'The controller returned to locomotion.'
            elif t < times['bow_end']:
                title, body = 'Bow allowed', 'A gentle stretch reminder, observed.'
            elif t < times['jump_denied']:
                title, body = 'A clear task boundary', 'Requests still need fresh measured state.'
            else:
                title, body = 'Jump declined', 'Outside this task. Input withheld.'
            d.rounded_rectangle((40, 1050, 1040, 1360), 24, fill=PALE)
            label(d, (76, 1090), title, 54, CORAL if t >= times['jump_denied'] else INK, True)
            label(d, (76, 1180), wrap(body, 900, 34), 34, spacing=14)
            measured = max((o for o in observations if o['time_s'] <= t), key=lambda o:o['time_s'], default=observations[0])
            label(d, (76, 1280), f'Measured edge clearance: {measured["table_margin_m"]:.3f} m', 30, MUTED)
            subtitle = next((c['text'] for c in captions if c['start'] <= t < c['end']), None)
            if subtitle:
                d.rounded_rectangle((40, 1430, 1040, 1645), 24, fill=INK)
                label(d, (76, 1470), wrap(subtitle, 900, 42), 42, CREAM, spacing=14)
            label(d, (40, 1760), 'clawmetry.com/physical-ai', 42, bold=True)
            label(d, (40, 1840), 'Simulation · actual controller evidence', 28, MUTED)
            writer.stdin.write(im.tobytes())
            if index == 5 * FPS:
                preview = im
    finally:
        writer.stdin.close()
        if writer.wait() != 0:
            raise RuntimeError('Portrait encoder failed')
        reader.stdout.close()
        reader.terminate()
        try:
            reader.wait(timeout=5)
        except subprocess.TimeoutExpired:
            reader.kill()
            reader.wait()
    command('ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', out / 'portrait-silent.mp4',
            '-ss', 12, '-t', 35, '-i', out / 'narration.wav', '-map', '0:v', '-map', '1:a',
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2', '-t', 35,
            '-movflags', '+faststart', out / 'Mizu-ClawMetry-Portrait-Review.mp4')
    (out / 'Mizu-ClawMetry-Portrait-Review.srt').write_text('\n\n'.join(
        f'{i+1}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"]}' for i, c in enumerate(captions)) + '\n')
    if preview:
        preview.save(out / 'portrait-review.png')
    final = out / 'Mizu-ClawMetry-Portrait-Review.mp4'
    manifest['portrait_export'] = {'file': final.name, 'duration_s': 35,
                                   'sha256': hashlib.sha256(final.read_bytes()).hexdigest(), 'source_speed': 1}
    (out / 'film-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--upstream', type=Path,
                   default=Path(__file__).resolve().parents[2] / 'clawmetry-jumper-upstream')
    p.add_argument('--source', type=Path,
                   help='Completed official replay MP4 with a built-in shared-journal report')
    p.add_argument('--voice-dir', type=Path, required=True,
                   help='Premium neural voice clips and manifest; no system voice fallback')
    p.add_argument('--brand', type=Path, required=True,
                   help='Official horizontal dark-background ClawMetry PNG lockup')
    p.add_argument('--reuse-lift', action='store_true',
                   help='Reuse the previously recorded local force clip and its shared-core report')
    p.add_argument('--portrait', action='store_true',
                   help='Also export the unsped 35-second official scene as a portrait excerpt')
    p.add_argument('--font', type=Path, help='Optional regular TrueType font; otherwise platform font then DejaVu Sans')
    p.add_argument('--bold-font', type=Path, help='Optional bold TrueType font')
    args = p.parse_args()
    root = args.root.resolve()
    global BRAND, FONT, BOLD
    if args.font:
        FONT = str(args.font)
    if args.bold_font:
        BOLD = str(args.bold_font)
    FONTS.clear()
    brand = Image.open(args.brand).convert('RGBA')
    brand = brand.crop(brand.getbbox())
    BRAND = brand.resize((236, round(236 * brand.height / brand.width)), Image.Resampling.LANCZOS)
    out = root / 'artifacts/film'
    out.mkdir(parents=True, exist_ok=True)
    source = (args.source or root / 'artifacts/shared-core-joints/mizu-built-in-joints.mp4').resolve()
    official_report = json.loads(source.with_suffix('.clawmetry.json').read_text())
    if not official_report['completed'] or official_report['resets'] or not official_report['finite']:
        raise RuntimeError('Official source footage must have a completed, finite, uninterrupted run')
    shared = official_report['shared_observer']
    if not shared['flushed'] or shared['incomplete'] or shared['errors'] or shared['dropped_total']:
        raise RuntimeError('The shared observation journal must be fully flushed without loss')
    journal_bytes = Path(shared['path']).read_bytes()
    events = [json.loads(line) for line in journal_bytes.splitlines()]
    if not events or any(e['run_id'] != shared['run_id'] for e in events):
        raise RuntimeError('The shared journal does not belong to the official source run')
    (out / 'official-shared-journal.jsonl').write_bytes(journal_bytes)
    observations = [e['data'] for e in events if e['kind'] == 'observation']
    if not observations or not observations[-1].get('joints'):
        raise RuntimeError('The official source must include measured named joint telemetry')
    clock, timeline = 0., []
    for event in events:
        if event['kind'] == 'observation':
            clock = event['data']['time_s']
        timeline.append((float(event['data'].get('time_s', clock)), event))
    def decision_time(action):
        return next(t for t, e in timeline if e['kind'] == 'guard.decision' and e['data']['action'] == action)
    def transition_time(target, *, after=0.):
        return next(t for t, e in timeline if t > after and e['kind'] == 'controller.receipt'
                    and e['data'].get('receipt_type') == 'mode_transition' and e['data'].get('to') == target)
    wave_at, bow_at, jump_at = (decision_time(action) for action in ('wave', 'bow', 'jump'))
    hello_end, bow_end = transition_time('locomotion', after=wave_at), transition_time('locomotion', after=bow_at)
    if args.reuse_lift:
        lift = out / 'scripted-lift-native.mp4'
        lift_report = json.loads((out / 'scripted-lift.report.json').read_text())
        health = lift_report['shared_observer']
        if not lift.is_file() or not lift_report['finite'] or not health['flushed'] or health['incomplete'] or health['errors'] or health['dropped_total']:
            raise RuntimeError('The retained native force clip must have complete shared-core evidence')
    else:
        lift, lift_report = lift_test(args.upstream, root / 'artifacts/official-scene/imported/scene.xml', out)
    lift_at = min(alert['time_s'] for alert in lift_report['alerts'] if alert['type'] == 'unexpected_lift')
    segments, captions = premium_audio(out, args.voice_dir)
    (out / 'Mizu-ClawMetry-Review-Draft.srt').write_text('\n\n'.join(
        f'{i+1}\n{stamp(s["start"])} --> {stamp(s["end"])}\n{s["text"]}' for i, s in enumerate(captions)) + '\n')
    (out / 'transcript.txt').write_text('\n\n'.join(s['text'] for s in segments) + '\n')
    (out / 'narration.json').write_text(json.dumps(segments, indent=2) + '\n')
    (out / 'captions.json').write_text(json.dumps(captions, indent=2) + '\n')
    command('ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', 6, '-i', source,
            '-frames:v', 1, out / 'official-wave.png')
    hero = Image.open(out / 'official-wave.png').convert('RGB')
    cards = {}
    intro = canvas('01 / A companion with a clear purpose')
    intro.paste(hero.resize((1067, 600)), (805, 210))
    d = ImageDraw.Draw(intro)
    label(d, (64, 220), 'Meet Mizu.', 84, bold=True)
    label(d, (68, 350), 'A calmer little presence\non your desk.', 42, spacing=18)
    label(d, (68, 570), 'Gentle moments.\nA clear record.', 36, MUTED, spacing=14)
    d.rounded_rectangle((68, 745, 640, 803), 22, fill=PALE)
    label(d, (90, 757), 'Powered by Jumper + ClawMetry', 26)
    cards['intro'] = intro

    today = canvas('02 / Useful now. Honest about what comes next.')
    d = ImageDraw.Draw(today)
    label(d, (72, 185), 'Sip. Stretch. Stay in flow.', 76, bold=True)
    for x, title, body, status in [(72, 'A gentle hello', 'A water reminder\nand a real wave.', 'WORKING IN SIMULATION'),
        (690, 'A small pause', 'A stretch reminder\nand a real bow.', 'WORKING IN SIMULATION'),
        (1308, 'More helpful skills', 'Cup delivery\nand desk tidying.', 'PLANNED / NOT VALIDATED')]:
        d.rounded_rectangle((x, 365, x+540, 815), 28, fill=PALE if x<1300 else '#eee9db')
        label(d, (x+32, 405), title, 36, bold=True)
        label(d, (x+32, 505), body, 34, spacing=18)
        label(d, (x+32, 735), status, 20, MUTED)
    cards['today'] = today

    history = canvas('04 / History you can review later')
    d = ImageDraw.Draw(history)
    label(d, (72, 170), 'Away from your desk?', 76, bold=True)
    label(d, (76, 280), 'The local record keeps decisions and actual behavior separate.', 34, MUTED)
    rows = [(f'{wave_at:06.3f} s', 'Wave request', 'Allowed', 'Native hello began'),
            (f'{hello_end:06.3f} s', 'Hello completed', 'Observed', 'Returned to idle'),
            (f'{bow_at:06.3f} s', 'Bow request', 'Allowed', 'Native bow began'),
            (f'{jump_at:06.3f} s', 'Jump request', 'Denied', 'Input withheld')]
    for i, row in enumerate(rows):
        y = 410 + i*108
        d.rounded_rectangle((72, y, 1848, y+85), 18, fill=PALE if i!=3 else '#f3e0d7')
        for x, text in zip((100, 390, 1010, 1310), row):
            label(d, (x, y+25), text, 30, CORAL if i==3 and x==1010 else INK)
    label(d, (78, 860), 'Actual shared ClawMetry journal. Named joints, requests and controller receipts.', 26, MUTED)
    cards['history'] = history

    status = canvas('06 / Alerts and delivery are different facts')
    d = ImageDraw.Draw(status)
    label(d, (72, 175), 'Notice the change.\nKeep the evidence.', 76, bold=True)
    label(d, (78, 400), 'Measured rise → local alert → notification receipt', 36)
    d.rounded_rectangle((76, 510, 1844, 820), 30, fill=PALE)
    label(d, (112, 548), 'LOCAL DETECTION', 24, MUTED)
    label(d, (112, 600), 'Lift and tilt alerts recorded', 42, bold=True)
    label(d, (1010, 548), 'PHONE DEMONSTRATION', 24, MUTED)
    label(d, (1010, 610), 'No delivery shown', 42, CORAL, True)
    label(d, (112, 720), 'A scene test does not identify who moved the robot or prove malicious intent.', 28, MUTED)
    label(d, (78, 860), 'No delivered phone notification or physical stop is claimed.', 26, MUTED)
    cards['status'] = status

    end = canvas('07 / Build the next chapter with us')
    d = ImageDraw.Draw(end)
    label(d, (76, 180), 'Useful little moments.\nA clearer record.', 84, bold=True)
    label(d, (82, 430), 'Open source. Real simulation evidence.', 42, MUTED)
    label(d, (82, 550), 'github.com/vivekchand/clawmetry', 42, bold=True)
    label(d, (82, 625), 'Mizu demo: github.com/vivekchand/clawmetry-jumper', 28, MUTED)
    label(d, (82, 700), 'clawmetry.com/physical-ai', 42)
    label(d, (82, 785), 'Web playground in preparation: clawmetry.com/jumper', 28, MUTED)
    label(d, (82, 860), 'Jumper assets/controller: KingKongRobotics  ·  Scene: official Jumper Design pipeline', 24, MUTED)
    cards['end'] = end

    def scene_frame(picture, t, *, lifted=False):
        im = canvas('05 / Separate scripted lift test' if lifted else '03 / The official simulator, at its original speed')
        picture = picture.resize((1408, 792), Image.Resampling.LANCZOS)
        im.paste(picture, (48, 150))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((1480, 150, 1872, 940), 24, fill=PALE)
        label(d, (1504, 180), 'SCRIPTED LIFT TEST' if lifted else 'TASK / REMINDERS', 22, MUTED)
        label(d, (1504, 240), f'{t:05.2f} s', 48, bold=True)
        if lifted:
            active = t>=lift_at
            title = 'Lift detected' if active else 'Observing'
            body = 'Measured base rise\nexceeded 6 cm.\n\nLocal alert recorded.' if active else 'The robot is observed\ncontinuously.\n\nExternal force:\n28 N upward\nfrom 2.0–2.3 s.'
            color = CORAL if active else INK
            foot = 'Native MuJoCo host.\nActual applied force.\nNo pose overrides.'
        else:
            if t<wave_at: title, body, color = 'Ready to help', 'Allowed task:\nwave + bow\n\nRequests need fresh\nmeasured state.', INK
            elif t<hello_end: title, body, color = 'Wave allowed', 'Input delivered.\n\nNative controller:\ngesture_hello\n\nPhysics still running.', INK
            elif t<bow_at: title, body, color = 'Back to idle', 'Native controller:\nlocomotion\n\nRecorded hello\ncompleted.', INK
            elif t<bow_end: title, body, color = 'Bow allowed', 'Input delivered.\n\nNative controller:\ngesture_bow\n\nA gentle stretch\nreminder.', INK
            elif t<jump_at: title, body, color = 'Back to idle', 'Native controller:\nlocomotion\n\nThe tabletop remains\nunder observation.', INK
            else: title, body, color = 'Jump denied', 'Outside this task.\n\nInput withheld.\n\nNo native jump\ntransition occurred.', CORAL
            measurement = max((o for o in observations if o['time_s'] <= t), key=lambda o:o['time_s'], default=observations[0])
            foot = f'Table clearance\n{measurement["table_margin_m"]:.3f} m measured\n\n{len(measurement["joints"])} named joints'
        label(d, (1504, 330), title, 30, color, True)
        label(d, (1504, 407), body, 26, spacing=13)
        label(d, (1504, 735), foot, 24, MUTED, spacing=12)
        label(d, (58, 117), 'When something changes, keep the evidence.' if lifted else 'A greeting with a clear task boundary.', 22, MUTED)
        return im

    source_reader, lift_reader = video_reader(source, 35), video_reader(lift, 6)
    writer = video_writer(out / 'film-silent.mp4', W, H)
    last_source, last_lift = hero, hero
    contact_times = {3, 9, 17, 29, 39, 50, 60, 69, 78}
    contact_images = []
    try:
        for number in range(DURATION * FPS):
            t = number / FPS
            if t<7: image = cards['intro'].copy()
            elif t<12: image = cards['today'].copy()
            elif t<47:
                last_source = next_frame(source_reader)
                if last_source is None:
                    raise RuntimeError('Official source ended before the unsped 35-second segment')
                image = scene_frame(last_source, t-12)
            elif t<57: image = cards['history'].copy()
            elif t<63:
                last_lift = next_frame(lift_reader)
                if last_lift is None:
                    raise RuntimeError('Lift source ended before its six-second segment')
                image = scene_frame(last_lift, t-57, lifted=True)
            elif t<74: image = cards['status'].copy()
            else: image = cards['end'].copy()
            subtitle = next((s['text'] for s in captions if s['start']<=t<s['end']), None)
            if subtitle:
                # Subtitles are also delivered separately as an editable SRT.
                d = ImageDraw.Draw(image)
                text = wrap(subtitle, 1590, 32)
                lines = text.count('\n')+1
                top = 978 - lines*37
                d.rounded_rectangle((110, top-14, 1810, 987), 16, fill='#193d33')
                box = d.multiline_textbbox((0,0), text, font=FONTS[32,False], spacing=8)
                d.multiline_text(((W-(box[2]-box[0]))/2, top), text, font=FONTS[32,False], fill=CREAM, spacing=8, align='center')
            writer.stdin.write(image.tobytes())
            if number%FPS==0 and int(t) in contact_times:
                contact_images.append(image.resize((640,360)))
            if number % (10*FPS)==0:
                print(f'Encoded review film {int(t)}/{DURATION} seconds', flush=True)
    finally:
        writer.stdin.close()
        if writer.wait()!=0: raise RuntimeError('Film encoder failed')
        for reader in (source_reader,lift_reader):
            # One initial/terminal frame can remain unread. Close the pipe
            # before waiting; FFmpeg otherwise blocks while flushing stdout.
            reader.stdout.close()
            reader.terminate()
            try:
                reader.wait(timeout=5)
            except subprocess.TimeoutExpired:
                reader.kill()
                reader.wait()
    sheet = Image.new('RGB',(1920,1080),CREAM)
    for i, image in enumerate(contact_images[:9]): sheet.paste(image,((i%3)*640,(i//3)*360))
    sheet.save(out / 'contact-sheet.jpg', quality=95)
    cards['intro'].save(out / 'review-poster.png')
    command('ffmpeg','-hide_banner','-loglevel','error','-y','-i',out/'film-silent.mp4',
            '-i',out/'narration.wav','-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-ac','2',
            '-t',DURATION,'-movflags','+faststart',out/'Mizu-ClawMetry-Review-Draft.mp4')
    metadata = {'duration_s':DURATION,'resolution':[W,H],'fps':FPS,'status':'review_draft_not_published',
                'official_source_unsped':str(source),'official_source_interval_s':[12,47],
                'official_report':official_report,'scripted_lift_report':lift_report,
                'shared_journal_sha256':hashlib.sha256(journal_bytes).hexdigest(),
                'shared_journal_run_id':shared['run_id'],
                'shared_timeline_s':{'wave':wave_at,'hello_end':hello_end,'bow':bow_at,'bow_end':bow_end,'jump_denied':jump_at},
                'observer_source':'https://github.com/vivekchand/clawmetry',
                'paid_visual_generation_used':False,'music_used':False,
                'voice':'fal / ElevenLabs Eleven v3 / Rachel',
                'audio_review_status':json.loads((args.voice_dir/'manifest.json').read_text()).get('listening_review', 'pending'),
                'official_brand_sha256':hashlib.sha256(args.brand.read_bytes()).hexdigest(),
                'scripted_lift_video_sha256':hashlib.sha256(lift.read_bytes()).hexdigest(),
                'phone_delivery_confirmed':False,'playground_status':'in preparation at build time'}
    (out/'film-manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    if args.portrait:
        portrait_excerpt(root)
    print(out/'Mizu-ClawMetry-Review-Draft.mp4')


if __name__=='__main__': main()
