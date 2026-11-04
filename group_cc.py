"""Group scan_cc.py hits per pattern by a normalized snippet, to spot shared library code.
Usage: group_cc.py hits.jsonl PATTERN [N]"""
import collections, json, re, sys
from urllib.parse import urlsplit

pat, n = sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 15
groups = collections.defaultdict(list)
for line in open(sys.argv[1]):
    r = json.loads(line)
    if pat + '_snips' not in r:
        continue
    s = r[pat + '_snips'][0]
    m = re.search(r'disabled', s)
    core = s[max(0, m.start() - 120):m.start() + 60] if m else s[:180]
    key = re.sub(r'\s+', ' ', re.sub(r'["\'][^"\']{0,80}["\']', '""', core))
    key = re.sub(r'\b\w{1,2}\b', 'x', key)[:160]
    groups[key].append(urlsplit(r['url']).hostname)
for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:n]:
    print(len(v), len(set(v)), repr(k[:160]))
print('groups', len(groups))
