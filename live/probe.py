"""Probe candidate pages for selector matches (total/visible). Usage: probe.py FIREFOX candidates.jsonl [extra selectors...]"""
import json, sys, time
from selenium import webdriver
o = webdriver.FirefoxOptions(); o.binary_location = sys.argv[1]; o.add_argument('-headless'); o.page_load_strategy = 'eager'
d = webdriver.Firefox(options=o); d.set_page_load_timeout(30); d.set_window_size(1366, 900)
extra = sys.argv[3:]
try:
    for l in open(sys.argv[2]):
        c = json.loads(l)
        try:
            d.get(c['url']); time.sleep(5)
            sels = [c['selector']] + extra
            res = d.execute_script("""return arguments[0].map(s => { let n = []; try { n = [...document.querySelectorAll(s)]; } catch (e) { return [s, 'bad']; }
              return [s, n.length, n.filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden').length]; })""", sels)
            print(c['id'], d.execute_script('return document.title.slice(0, 50)'), res, flush=True)
        except Exception as e:
            print(c['id'], 'ERR', str(e)[:100], flush=True)
finally:
    d.quit()
