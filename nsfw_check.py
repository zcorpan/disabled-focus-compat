# Flags adult pages in compare.py's output, so they're marked nsfw and get a repro test instead of
# review images. Page signals: an adult <meta name="rating"> (recorded by harness.py) and the host
# being blocked by Cloudflare's family resolver (which also blocks malware). Images: NudeNet
# (pip install nudenet) finding exposed nudity in a 400px tile. It errs toward flagging: nude
# paintings and sculpture get flagged, lingerie and swimwear pass. Adult content without nudity
# isn't caught, so also flag by eye. Downscaled images (review pairs) are caught less often.
# Writes <out-dir>/nsfw.csv (idx, page, reasons), keeping rows already there (add pages by hand).
# Run after compare.py and before analyze.py. publish_check.py runs check() on staged images.
# Usage: nsfw_check.py <out-dir>
import csv, glob, json, os, re, sys, urllib.parse, urllib.request
from PIL import Image
import ocr_check

ADULT_RATING = re.compile(r'RTA-5042-1996-1400-1577-RTA|\badult\b', re.I)
EXPOSED = {'FEMALE_GENITALIA_EXPOSED', 'MALE_GENITALIA_EXPOSED', 'FEMALE_BREAST_EXPOSED',
           'ANUS_EXPOSED', 'BUTTOCKS_EXPOSED'}
THRESHOLD = 0.4  # tuned on adult, lingerie, swimwear, painting and other pages
_detector = None


def backend():
    global _detector
    if _detector is None:
        try:
            from nudenet import NudeDetector
        except ImportError:
            return None
        _detector = NudeDetector()
    return _detector


def check(paths):
    """Returns [(path, x, y, label, score)] for exposed nudity in any tile of the images."""
    det = backend()
    hits = []
    for path in paths:
        for x, y, tile in ocr_check.tiles(Image.open(path), tile=400, overlap=66, scale=1):
            for d in det.detect(ocr_check.png_bytes(tile)):
                if d['class'] in EXPOSED and d['score'] >= THRESHOLD:
                    hits.append((path, x, y, d['class'], round(d['score'], 2)))
    return hits


def family_blocked(host, cache={}):
    if host not in cache:
        req = urllib.request.Request(
            'https://family.cloudflare-dns.com/dns-query?' + urllib.parse.urlencode({'name': host, 'type': 'A'}),
            headers={'accept': 'application/dns-json'})
        try:
            answers = json.load(urllib.request.urlopen(req, timeout=10)).get('Answer', [])
            cache[host] = any(a.get('data') == '0.0.0.0' for a in answers)
        except Exception:
            cache[host] = None
    return cache[host]


def flag_pages(out_dir):
    """Returns {idx: (page, {reason})} from the recorded ratings and family DNS."""
    flags = {}
    for r in map(json.loads, open(f'{out_dir}/results.jsonl')):
        reasons = set()
        for v in (r.get(t) or {} for t in ('A', 'A2', 'B')):
            if any(ADULT_RATING.search(m.get('rating') or '') for m in [v] + v.get('frames', [])):
                reasons.add('adult rating meta')
        host = urllib.parse.urlsplit(r['page']).hostname
        blocked = family_blocked(host) if host else False
        if blocked:
            reasons.add('family DNS block')
        elif blocked is None:
            print('family DNS lookup failed for', host)
        if reasons:
            flags[r['idx']] = (r['page'], reasons)
    return flags


if __name__ == '__main__':
    out_dir = sys.argv[1]
    path = f'{out_dir}/nsfw.csv'
    pages = {r['idx']: r['page'] for r in map(json.loads, open(f'{out_dir}/results.jsonl'))}
    flags = {}
    if os.path.exists(path):
        flags = {int(r['idx']): (r['page'], set(filter(None, r['reasons'].split('; '))))
                 for r in csv.DictReader(open(path))}
    for idx, (page, reasons) in flag_pages(out_dir).items():
        flags.setdefault(idx, (page, set()))[1].update(reasons)
    if backend():
        for shot, x, y, label, score in check(sorted(glob.glob(f'{out_dir}/shots/*.png'))):
            idx = int(os.path.basename(shot).split('-')[0])
            flags.setdefault(idx, (pages.get(idx, ''), set()))[1].add('nudity in screenshot')
    else:
        print('no image check: pip install nudenet')
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['idx', 'page', 'reasons'])
        for idx in sorted(flags):
            w.writerow([idx, flags[idx][0], '; '.join(sorted(flags[idx][1]))])
    print(len(flags), 'pages flagged in', path)
    sys.exit(0 if backend() else 1)
