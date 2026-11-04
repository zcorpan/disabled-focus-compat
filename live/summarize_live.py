"""Summarize live results per candidate and setup: events from first key mark on, with log from
the previous page (sessionStorage) when the page navigated. Usage: summarize_live.py OUTDIR"""
import json, sys, collections
rows = [json.loads(l) for l in open(sys.argv[1] + '/results.jsonl')]
by = collections.defaultdict(dict)
for r in rows:
    by[r['id']][r['setup']] = r
KIND = {'keydown-enter': 'K', 'disable-focused': 'D', 'fetch': 'F', 'xhr': 'X', 'form.submit': 'S',
        'form.requestSubmit': 'S', 'submit-event': 'E', 'blur': 'B', 'beforeunload': 'U'}
def seq(evs):
    out, on = [], False
    for e in evs or []:
        if e['kind'] == 'mark-start': on = True; continue
        if not on: continue
        if e['kind'].startswith('mark-key'): out.append('|'); continue
        k = KIND.get(e['kind'])
        if not k: continue
        if k == 'K': k += '(' + ('dis' if e.get('disabled') else e.get('target', '')[:12]) + ')'
        out.append(k)
    return ' '.join(out)
for cid, s in by.items():
    print('##', cid)
    for tag in ['A', 'A2', 'B', 'C']:
        r = s.get(tag)
        if not r: continue
        if 'error' in r and not r.get('log'):
            print(f'  {tag}: ERROR {r["error"]}'); continue
        prev = r.get('prev') or {}
        early = r.get('log_early')
        log = early if early and any(e['kind'] == 'mark-start' for e in early) else (prev.get('ev') if prev else None) or r.get('log')
        print(f'  {tag}: active={r.get("active")} same_url={r.get("same_url")} :: {seq(log)}')
