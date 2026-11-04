"""Prefilter Common Crawl HTML for script patterns that could observe a focused control being
disabled (whatwg/html#13170). Only inline scripts and inline event handler attributes are visible.

Usage: scan_cc.py OUT.jsonl WARC...
Writes one line per page with any pattern hit (url, counts, up to 3 snippets per pattern), and a
final {"totals": ...} line.
"""
import json
import multiprocessing as mp
import re
import sys

from cc import html_responses

SCRIPT = re.compile(r'<script\b[^>]*>(.*?)</script\s*>', re.S | re.I)
HANDLER = re.compile(r'''\s(on[a-z]+)\s*=\s*("[^"]*"|'[^']*')''', re.I)

# Disabling a form control (or fieldset) from script.
DIS = re.compile(
    r'''\.disabled\s*=\s*(?:true|!0|1\b|["']disabled["'])'''
    r'''|\.prop\(\s*["']disabled["']\s*,\s*(?:true|!0)'''
    r'''|\.attr\(\s*["']disabled["']\s*,\s*["'](?:disabled|true)["']'''
    r'''|setAttribute\(\s*["']disabled["']''', re.I)
# Keyboard handling, Enter in particular.
ENTER = re.compile(r'''(?:keyCode|which|charCode)\s*={2,3}\s*13\b|\.key\s*={2,3}\s*["']Enter["']'''
                   r'''|["']Enter["']\s*={2,3}\s*\w+\.key\b|13\s*={2,3}\s*\w+\.(?:keyCode|which)''')
KEY = re.compile(r'''\bon(?:keydown|keypress|keyup)\b|["'](?:keydown|keypress|keyup)["']'''
                 r'''|\.(?:keydown|keypress|keyup)\(''', re.I)
BLUR = re.compile(r'''\bon(?:blur|focusout)\b|["'](?:blur|focusout)["']|\.(?:blur|focusout)\(\s*function''',
                  re.I)
ACTIVE = re.compile(r'\bactiveElement\b')
# Self-disable in a click/submit handler attribute: the case the change targets.
SELF = re.compile(r'''\bthis\.disabled\s*=\s*(?:true|!0|1\b|["']disabled["'])''', re.I)

WINDOW = 600


def near(text, a, b, window=WINDOW):
    """Spans where a match of b starts within window chars of a match of a."""
    out = []
    bs = [m.start() for m in b.finditer(text)]
    if not bs:
        return out
    for m in a.finditer(text):
        for s in bs:
            if abs(s - m.start()) <= window:
                lo, hi = min(s, m.start()), max(s, m.end())
                out.append((lo, hi))
                break
    return out


def snip(text, lo, hi, pad=200):
    return text[max(0, lo - pad):min(len(text), hi + pad)][:1500]


def scan_page(html):
    blocks = SCRIPT.findall(html)
    handlers = HANDLER.findall(html)
    res = {}
    code_blocks = blocks + [v[1:-1] for _, v in handlers]
    if not any(DIS.search(b) for b in code_blocks):
        return None
    res['dis'] = sum(len(DIS.findall(b)) for b in code_blocks)
    for name, pat in (('enter', ENTER), ('key', KEY), ('blur', BLUR), ('active', ACTIVE)):
        spans = []
        for b in code_blocks:
            spans += [snip(b, lo, hi) for lo, hi in near(b, DIS, pat)]
        if spans:
            res[name] = len(spans)
            res[name + '_snips'] = spans[:3]
    # Inline key handler attribute on a control, plus disabling somewhere on the page.
    key_attrs = [v for n, v in handlers if n.lower() in ('onkeydown', 'onkeypress', 'onkeyup')]
    if key_attrs:
        res['keyattr'] = len(key_attrs)
        res['keyattr_snips'] = [v[:300] for v in key_attrs[:3]]
    self_dis = [v for n, v in handlers if n.lower() in ('onclick', 'onsubmit') and SELF.search(v)]
    if self_dis:
        res['selfclick'] = len(self_dis)
        res['selfclick_snips'] = [v[:300] for v in self_dis[:3]]
    return res


def scan_warc(path):
    pages = 0
    hits = []
    for url, html in html_responses(path):
        pages += 1
        try:
            r = scan_page(html)
        except Exception:  # noqa: BLE001
            continue
        if r:
            r['url'] = url
            r['warc'] = path.rsplit('/', 1)[-1]
            hits.append(r)
    return pages, hits


def main():
    out, warcs = sys.argv[1], sys.argv[2:]
    totals = {'pages': 0}
    with mp.Pool(min(len(warcs), 12)) as pool, open(out, 'w') as f:
        for pages, hits in pool.imap_unordered(scan_warc, warcs):
            totals['pages'] += pages
            for h in hits:
                f.write(json.dumps(h) + '\n')
                for k in ('dis', 'enter', 'key', 'blur', 'active', 'keyattr', 'selfclick'):
                    if k in h:
                        totals[k] = totals.get(k, 0) + 1
            print(pages, len(hits), flush=True)
        f.write(json.dumps({'totals': totals}) + '\n')
    print(totals)


if __name__ == '__main__':
    main()
