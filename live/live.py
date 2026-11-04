"""Live check: focus a page's control, type, press Enter twice; compare Firefox pref off (A, A2)
and on (B) in the same build. Records what the preload script logs (scrubbed URLs, no query strings).

Usage: live.py FIREFOX_BINARY candidates.jsonl OUTDIR
candidates.jsonl lines: {"id", "url", "selector", "text", "keys": ["Enter", "Enter"], "note"}
"""
import json
import os
import pathlib
import re
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

PRELOAD = pathlib.Path(__file__).with_name("preload.js").read_text()
KEYS = {"Enter": Keys.ENTER, "Escape": Keys.ESCAPE, "Space": Keys.SPACE, "Tab": Keys.TAB, "ArrowDown": Keys.ARROW_DOWN}
SETUPS = [("A", False), ("A2", False), ("B", True), ("C", True)]
VARIANT = pathlib.Path(__file__).with_name("variant.js").read_text()


def scrub(s):
    s = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "<ip>", str(s))
    return s


def driver(binary, on, variant=False):
    o = webdriver.FirefoxOptions()
    o.binary_location = binary
    o.add_argument("-headless")
    o.enable_bidi = True
    o.set_preference("dom.forms.retain_focus_on_disabled.enabled", on)
    o.page_load_strategy = "eager"
    d = webdriver.Firefox(options=o)
    d.set_page_load_timeout(30)
    d.set_window_size(1366, 900)
    if variant:
        d.script.pin(VARIANT)
    d.script.pin(PRELOAD)
    return d


def visit(d, c, shots, tag):
    rec = {"id": c["id"], "setup": tag}
    try:
        d.get(c["url"])
    except Exception as e:  # noqa: BLE001
        rec["load_error"] = str(e)[:120]
    time.sleep(c.get("wait", 5))
    if c.get("scroll"):
        d.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        d.execute_script("window.scrollTo(0, 0)")
        time.sleep(1)
    els = d.execute_script("""return [...document.querySelectorAll(arguments[0])].filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden')""", c["selector"])
    if not els:
        rec["error"] = "selector not found or not visible"
        return rec
    el = els[0]
    d.execute_script("arguments[0].scrollIntoView({block: 'center'})", el)
    try:
        el.click()
    except Exception:  # noqa: BLE001
        d.execute_script("arguments[0].focus()", el)
    time.sleep(0.5)
    if c.get("text"):
        ActionChains(d).send_keys(c["text"]).perform()
    d.execute_script("window.__dfc && window.__dfc.ev.push({t: Math.round(performance.now() - __dfc.t0), kind: 'mark-start'})")
    for i, k in enumerate(c.get("keys", ["Enter", "Enter"])):
        try:
            ActionChains(d).send_keys(KEYS.get(k, k)).perform()
        except Exception as e:  # noqa: BLE001
            rec.setdefault("key_errors", []).append(str(e)[:80])
        time.sleep(c.get("gap", 1.5) if i + 1 < len(c.get("keys", ["Enter", "Enter"])) else 0.3)
        try:
            d.execute_script("window.__dfc && window.__dfc.ev.push({t: Math.round(performance.now() - __dfc.t0), kind: 'mark-key%d'})" % (i + 1))
        except Exception:  # noqa: BLE001
            pass
    try:
        rec["log_early"] = d.execute_script("return window.__dfc ? window.__dfc.ev : null")
    except Exception:  # noqa: BLE001
        pass
    time.sleep(3)
    try:
        rec["log"] = d.execute_script("return window.__dfc ? window.__dfc.ev : null")
        rec["prev"] = d.execute_script("return window.__dfc ? window.__dfc.prev : null")
        rec["active"] = d.execute_script("const a = document.activeElement; return a ? a.nodeName + (a.id ? '#' + a.id : '') + (a.disabled ? '[disabled]' : '') : null")
        rec["same_url"] = d.current_url.split("?")[0].split("#")[0] == c["url"].split("?")[0].split("#")[0]
        d.save_screenshot(os.path.join(shots, f"{c['id']}-{tag}.png"))
    except Exception as e:  # noqa: BLE001
        rec["error"] = "after: " + str(e)[:120]
    return json.loads(scrub(json.dumps(rec)))


def main():
    binary, cands, out = sys.argv[1:4]
    only = sys.argv[4].split(",") if len(sys.argv) > 4 else ["A", "A2", "B"]
    shots = os.path.join(out, "shots")
    os.makedirs(shots, exist_ok=True)
    cs = [json.loads(l) for l in open(cands) if l.strip()]
    with open(os.path.join(out, "results.jsonl"), "a") as f:
        for tag, on in SETUPS:
            if tag not in only:
                continue
            d = driver(binary, on, tag == "C")
            try:
                for c in cs:
                    try:
                        r = visit(d, c, shots, tag)
                    except Exception as e:  # noqa: BLE001
                        r = {"id": c["id"], "setup": tag, "error": str(e)[:150]}
                        d.quit()
                        d = driver(binary, on, tag == "C")
                    f.write(json.dumps(r) + "\n")
                    f.flush()
                    print(tag, c["id"], r.get("error", "ok"), flush=True)
            finally:
                d.quit()


if __name__ == "__main__":
    main()
