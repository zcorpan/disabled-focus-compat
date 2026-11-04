"""Print run_impl.py output compactly. Usage: show.py a.jsonl [b.jsonl] [names...]"""
import json, sys
files = [a for a in sys.argv[1:] if a.endswith('.jsonl')]
names = set(a for a in sys.argv[1:] if not a.endswith('.jsonl'))
runs = [{r['name']: r for r in map(json.loads, open(f)) if 'name' in r} for f in files]
def fmt(o):
    if 'js' in o: return 'js=' + json.dumps(o['js'])
    ev = [e for e in o['log'] if not e.startswith(('keyup', 'keypress'))]
    st = {k: v for k, v in o.items() if k not in ('log', 'active', 'scrollY', 'cnt')}
    bits = [f"act={o['active']}"]
    if o['scrollY']: bits.append(f"scroll={o['scrollY']}")
    if o['cnt']: bits.append('cnt=' + json.dumps(o['cnt']))
    for k, v in st.items(): bits.append(f"{k}=" + json.dumps(v).replace('"', '').replace(' ', ''))
    if ev: bits.append('ev=[' + ','.join(ev) + ']')
    return ' '.join(bits)
for name in runs[0]:
    if names and name not in names: continue
    print('##', name)
    for f, run in zip(files, runs):
        r = run.get(name, {})
        if 'error' in r: print(' ', f, 'ERROR', r['error'][:200]); continue
        for i, o in enumerate(r.get('out', [])): print(f'  {f[:-6]}[{i}]', fmt(o))
