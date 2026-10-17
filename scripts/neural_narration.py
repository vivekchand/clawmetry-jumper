#!/usr/bin/env python3
"""Optional premium narration tooling, never part of the ClawMetry observer.

Public API: https://fal.ai/models/fal-ai/elevenlabs/tts/eleven-v3/api
Explicit --generate is required for paid requests. Only authored text is sent.
Receipts survive interrupted runs; an ambiguous submission is never retried.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MODEL = 'fal-ai/elevenlabs/tts/eleven-v3'
VOICE = 'Rachel'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def credential():
    value = os.environ.get('FAL_KEY', '').strip()
    if value:
        if any(ord(c) < 32 for c in value):
            raise RuntimeError('The narration credential contains invalid control characters')
        return value
    filename = os.environ.get('FAL_CREDENTIALS_FILE')
    if filename:
        raw = Path(filename).expanduser().read_text().strip()
        if raw.startswith('{'):
            data = json.loads(raw)
            value = data.get('FAL_KEY') or data.get('FAL_API_KEY')
        else:
            match = re.search(r'(?m)^\s*(?:export\s+)?FAL_(?:API_)?KEY\s*=\s*(.+?)\s*$', raw)
            value = match.group(1).strip().strip('\"\'') if match else (raw if '\n' not in raw and not raw.startswith('#') else None)
        if isinstance(value, str) and value.strip():
            if any(ord(c) < 32 for c in value):
                raise RuntimeError('The narration credential contains invalid control characters')
            return value.strip()
    raise RuntimeError('Premium narration needs FAL_KEY or FAL_CREDENTIALS_FILE; no system voice fallback')


def save(path, value):
    temporary = path.with_suffix('.pending')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def queue_request(url, key, payload=None):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'queue.fal.run':
        raise RuntimeError('Refusing to send a credential to an unexpected queue host')
    request = Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={'Authorization': 'Key ' + key, 'Content-Type': 'application/json'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=45) as response:
            data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise RuntimeError('Queue response exceeds its metadata bound')
            return json.loads(data)
    except HTTPError as exc:
        raise RuntimeError(f'Premium narration HTTP {exc.code}; inspect the retained receipt before retrying') from None


def queued_result(payload, jobs):
    digest = hashlib.sha256(json.dumps([MODEL, payload], sort_keys=True).encode()).hexdigest()
    jobs.mkdir(parents=True, exist_ok=True)
    receipt = jobs / (digest + '.json')
    if receipt.exists():
        job = json.loads(receipt.read_text())
        if job.get('model') != MODEL or job.get('input') != payload:
            raise RuntimeError('Narration cache does not match its authored input')
    else:
        key = credential()  # Fail before writing a submission intent if access is absent.
        job = {'model': MODEL, 'input': payload, 'state': 'submitting'}
        try:
            # Exclusive creation also prevents two simultaneous invocations
            # from both making a paid POST for the same authored clip.
            with receipt.open('x') as stream:
                json.dump(job, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            return queued_result(payload, jobs)
        result = queue_request('https://queue.fal.run/' + MODEL, key, payload)
        job.update(result)
        job['state'] = 'queued'
        save(receipt, job)
    if 'result' in job:
        return job['result']
    if not job.get('status_url') or not job.get('response_url'):
        raise RuntimeError('Submission is ambiguous; inspect its receipt/account, do not automatically resubmit')
    key = credential()
    for _ in range(120):
        state = queue_request(job['status_url'], key)
        if state.get('status') == 'COMPLETED':
            if state.get('error'):
                raise RuntimeError('Premium narration failed; receipt retained')
            result = queue_request(job['response_url'], key)
            job.update(state='completed', result=result)
            save(receipt, job)
            return result
        time.sleep(5)
    raise RuntimeError('Narration remains queued; rerun to resume this receipt without a new paid POST')


def narration(text, destination, jobs):
    if not isinstance(text, str) or not 1 <= len(text) <= 4000:
        raise ValueError('Supply a bounded authored narration clip')
    payload = {'text': text, 'voice': VOICE, 'stability': .5, 'language_code': 'en', 'timestamps': True}
    result = queued_result(payload, jobs)
    url = result['audio']['url']
    if urlsplit(url).scheme != 'https':
        raise RuntimeError('Narration media must use HTTPS')
    # Media fetches carry no credential and cannot follow redirects.
    with build_opener(NoRedirect()).open(Request(url), timeout=60) as response:
        audio = response.read(16_000_001)
    if not audio or len(audio) > 16_000_000:
        raise RuntimeError('Narration media is empty or exceeds its size bound')
    destination.write_bytes(audio)
    save(destination.with_suffix('.speech.json'), {'model': MODEL, 'voice': VOICE, 'text': text,
         'timestamps': result.get('timestamps', []), 'audio_url': url})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true', help='Explicitly authorize paid premium narration requests')
    parser.add_argument('--audition', action='store_true', help='Generate only a short representative sample')
    parser.add_argument('--out', type=Path, default=Path('artifacts/film/premium-voice'))
    args = parser.parse_args()
    if not args.generate:
        parser.error('--generate is required; this optional tool can incur provider charges')
    args.out.mkdir(parents=True, exist_ok=True)
    if args.audition:
        narration('Meet Mizu. ClawMetry keeps a record. A greeting in the official Jumper simulator.',
                  args.out / 'audition.mp3', args.out / 'jobs')
        print('Premium audition prepared. Listening review is required; none is claimed by this tool.')
        return
    tree = ast.parse(Path(__file__).with_name('build_film.py').read_text())
    clips = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == 'NARRATION' for target in node.targets))
    manifest = {'model': MODEL, 'voice': VOICE, 'listening_review': 'pending', 'clips': []}
    for index, (start, end, text) in enumerate(clips):
        path = args.out / f'voice-{index:02}.mp3'
        prior = path.with_suffix('.speech.json')
        metadata = json.loads(prior.read_text()) if prior.exists() else {}
        if not path.exists() or metadata.get('text') != text or metadata.get('model') != MODEL or metadata.get('voice') != VOICE:
            narration(text, path, args.out / 'jobs')
        duration = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
            'format=duration', '-of', 'default=nw=1:nk=1', str(path)], text=True))
        manifest['clips'].append({'index': index, 'text': text, 'duration_s': duration,
             'available_s': end-start, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        save(args.out / 'manifest.json', manifest)
        print(f'Premium narration clip {index+1}/{len(clips)} ready; listening review pending')


if __name__ == '__main__':
    main()
