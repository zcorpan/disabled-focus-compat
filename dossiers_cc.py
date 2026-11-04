"""Write one dossier per normalized snippet group for a pattern (untrusted crawl material).
Usage: dossiers_cc.py hits.jsonl PATTERN OUTDIR [MAX_GROUPS] [SEED]"""
import collections, json, os, random, re, sys
from urllib.parse import urlsplit

src, pat, outdir = sys.argv[1:4]
maxg = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
seed = sys.argv[5] if len(sys.argv) > 5 else '13170'
groups = collections.defaultdict(list)
for line in open(src):
    r = json.loads(line)
    if pat + '_snips' not in r or r.get('_skip'):
        continue
    s = r[pat + '_snips'][0]
    m = re.search(r'disabled', s)
    core = s[max(0, m.start() - 120):m.start() + 60] if m else s[:180]
    key = re.sub(r'\s+', ' ', re.sub(r'["\'][^"\']{0,80}["\']', '""', core))
    key = re.sub(r'\b\w{1,2}\b', 'x', key)[:160]
    groups[key].append(r)
keys = sorted(groups, key=lambda k: (-len(groups[k]), k))
if len(keys) > maxg:
    rnd = random.Random(seed)
    keys = sorted(rnd.sample(keys, maxg), key=lambda k: (-len(groups[k]), k))
os.makedirs(outdir, exist_ok=True)
index = []
for i, k in enumerate(keys):
    rs = groups[k]
    gid = f'{pat}-{i:03d}'
    with open(os.path.join(outdir, gid + '.txt'), 'w') as f:
        f.write(f'group {gid}: {len(rs)} pages on {len({urlsplit(r["url"]).hostname for r in rs})} hosts\n')
        f.write('example URL: ' + rs[0]['url'] + '\n\n')
        for j, s in enumerate(rs[0][pat + '_snips']):
            f.write(f'--- snippet {j + 1} (inline script or handler attribute, +-200 chars) ---\n{s}\n\n')
        if len(rs) > 1:
            f.write(f'--- snippet 1 from a second page ({rs[1]["url"]}) ---\n{rs[1][pat + "_snips"][0]}\n')
    index.append({'group': gid, 'pages': len(rs), 'hosts': len({urlsplit(r['url']).hostname for r in rs}),
                  'urls': [r['url'] for r in rs]})
with open(os.path.join(outdir, 'index.jsonl'), 'w') as f:
    for x in index:
        f.write(json.dumps(x) + '\n')
print(len(groups), 'groups;', len(index), 'written')
