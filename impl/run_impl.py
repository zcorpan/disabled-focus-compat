"""Run disabled-focus scenarios with real WebDriver key input. Prints one JSON line per scenario.

Usage: run_impl.py firefox <binary> <on|off> | run_impl.py chrome <binary> <chromedriver>
"""
import json
import pathlib
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

URL = pathlib.Path(__file__).with_name("page.html").as_uri()
K = Keys
FORM = '<form id="f" action="javascript:void 0">{}<button id="sub">sub</button></form><button id="after">after</button>'
DISABLE = "async id => { const el = document.getElementById(id); el.disabled = true; log.push('--disabled--'); await frames2(); }"

def dis(id_):
    return ("ajs", f"await ({DISABLE})('{id_}')")


def focus(id_):
    return ("js", f"document.getElementById('{id_}').focus()")


S = {}

S["keydown-self-disable-textarea"] = [
    ("html", '<textarea id="t"></textarea><button id="after">after</button>'),
    ("js", "window.cnt={sends:0}; t.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); cnt.sends++; t.disabled = true; } })"),
    focus("t"), ("keys", "hi"), ("keys", K.ENTER), ("ajs", "await frames2()"), ("snap", ["t"]),
    ("keys", K.ENTER), ("keys", "x"), ("snap", ["t"])]

S["keydown-on-input-disables-button"] = [
    ("html", '<input id="q"><button id="go">go</button>'),
    ("js", "window.cnt={searches:0}; q.addEventListener('keydown', e => { if (e.key === 'Enter') { cnt.searches++; q.disabled = true; go.disabled = true; } })"),
    focus("q"), ("keys", "hi"), ("keys", K.ENTER), ("ajs", "await frames2()"), ("snap", ["q"]),
    ("keys", K.ENTER), ("snap", ["q"])]

S["button-onclick-self-disable"] = [
    ("html", '<button id="b">b</button><button id="after">after</button>'),
    ("js", "window.cnt={clicks:0}; b.onclick = () => { cnt.clicks++; b.disabled = true; }"),
    focus("b"), ("keys", K.ENTER), ("ajs", "await frames2()"), ("snap", ["b"]),
    ("keys", K.ENTER), ("keys", K.SPACE), ("snap", ["b"]), ("keys", K.TAB), ("snap", ["b"])]

for t in ["text", "email", "search", "password", "number", "date", "time", "color", "file",
          "range", "checkbox", "radio", "submit", "image", "reset"]:
    S[f"implicit-submit-{t}"] = [
        ("html", FORM.format(f'<input type="{t}" id="i" value="1">')),
        focus("i"), dis("i"), ("snap", ["i"]), ("keys", K.ENTER), ("ajs", "await frames2()"),
        ("snap", ["i"])]

S["reset-button-enter-space"] = [
    ("html", FORM.format('<input id="txt" value="orig"><button type="reset" id="r">reset</button>')),
    ("js", "txt.value = 'edited'"), focus("r"), dis("r"), ("keys", K.ENTER), ("keys", K.SPACE),
    ("ajs", "await frames2()"), ("snap", ["txt", "r"])]

S["radio-keys"] = [
    ("html", FORM.format('<input type="radio" name="g" id="r1" checked><input type="radio" name="g" id="r2"><input type="radio" name="g" id="r3">')),
    focus("r1"), dis("r1"), ("keys", K.ARROW_DOWN), ("snap", ["r1", "r2"]), ("keys", K.ARROW_RIGHT),
    ("snap", ["r1", "r2", "r3"]), ("keys", K.SPACE), ("snap", ["r1", "r2", "r3"])]

S["checkbox-space"] = [
    ("html", FORM.format('<input type="checkbox" id="c">')),
    focus("c"), dis("c"), ("keys", K.SPACE), ("snap", ["c"])]

S["select-keys"] = [
    ("html", '<select id="s"><option>a</option><option>b</option><option>c</option></select>'),
    focus("s"), dis("s"), ("keys", "b"), ("snap", ["s"]), ("keys", K.ARROW_DOWN), ("keys", K.END),
    ("snap", ["s"]), ("keys", K.SPACE), ("keys", K.ENTER), ("snap", ["s"]),
    ("altdown",), ("snap", ["s"])]

S["select-multiple-keys"] = [
    ("html", '<select id="s" multiple><option>a</option><option>b</option><option>c</option></select>'),
    focus("s"), dis("s"), ("keys", K.ARROW_DOWN), ("keys", K.SPACE), ("snap", ["s"])]

S["base-select-open-then-disable"] = [
    ("html", '<select id="s" class="base"><option id="o1">a</option><option id="o2">b</option></select>'),
    ("click", "s"), ("sleep", 0.3), ("snap", ["s"]), dis("s"), ("snap", ["s"]),
    ("keys", K.ARROW_DOWN), ("keys", K.ENTER), ("snap", ["s"])]

S["base-select-keys-disabled"] = [
    ("html", '<select id="s" class="base"><option>a</option><option>b</option></select>'),
    focus("s"), dis("s"), ("keys", K.ENTER), ("snap", ["s"]), ("keys", K.SPACE), ("snap", ["s"]),
    ("keys", K.ARROW_DOWN), ("snap", ["s"])]

S["text-edit-then-disable-then-tab"] = [
    ("html", '<input id="t" minlength="5"><button id="after">after</button>'),
    focus("t"), ("keys", "abc"), ("snap", ["t"]), dis("t"), ("snap", ["t"]), ("keys", K.TAB),
    ("snap", ["t"]), ("js", "t.disabled = false"), ("ajs", "await frames2()"), ("snap", ["t"])]

S["text-editing-shortcuts-disabled"] = [
    ("html", '<input id="t"><button id="after">after</button>'),
    focus("t"), ("keys", "abc"), dis("t"), ("chord", K.META, "z"), ("snap", ["t"]),
    ("chord", K.META, "a"), ("keys", K.BACKSPACE), ("snap", ["t"]), ("chord", K.META, "x"),
    ("snap", ["t"])]

S["number-range-keys"] = [
    ("html", '<input type="number" id="n" value="5"><input type="range" id="r" value="50">'),
    focus("n"), dis("n"), ("keys", K.ARROW_UP), ("snap", ["n"]),
    focus("r"), ("ajs", "await frames2()"), ("snap", ["r"]),
    ("js", "n.disabled = false"), focus("r"), dis("r"), ("keys", K.END), ("keys", K.ARROW_LEFT),
    ("snap", ["r"])]

S["shift-tab-from-disabled"] = [
    ("html", '<button id="before">before</button><button id="b">b</button><button id="after">after</button>'),
    focus("b"), dis("b"), ("shifttab",), ("snap", ["b"])]

S["reenable-and-type"] = [
    ("html", '<fieldset id="fs"><input id="t"></fieldset>'),
    focus("t"), ("ajs", "fs.disabled = true; log.push('--disabled--'); await frames2()"),
    ("snap", ["t"]), ("keys", "x"), ("snap", ["t"]),
    ("ajs", "fs.disabled = false; await frames2()"), ("keys", "y"), ("snap", ["t"])]

S["iframe-input"] = [
    ("html", '<iframe id="fr" srcdoc="<input id=i>"></iframe><button id="after">after</button>'),
    ("ajs", "if (!(fr.contentDocument && fr.contentDocument.URL === 'about:srcdoc' && fr.contentDocument.readyState === 'complete')) await new Promise(r => fr.onload = r); installLog(fr.contentDocument, 'fr:')"),
    ("js", "fr.contentWindow.focus(); fr.contentDocument.getElementById('i').focus()"),
    ("ajs", "fr.contentDocument.getElementById('i').disabled = true; log.push('--disabled--'); await frames2()"),
    ("js", "return {top: document.activeElement.id, inner: fr.contentDocument.activeElement.id, hasFocus: fr.contentDocument.hasFocus()}"),
    ("keys", "x"), ("snap", []), ("keys", K.TAB), ("snap", [])]

S["shadow-dom-button"] = [
    ("html", '<div id="host"></div><button id="after">after</button>'),
    ("js", "const sr = host.attachShadow({mode: 'open'}); sr.innerHTML = '<button id=sb>sb</button>'; sr.getElementById('sb').focus()"),
    ("ajs", "host.shadowRoot.getElementById('sb').disabled = true; log.push('--disabled--'); await frames2()"),
    ("js", "return {doc: document.activeElement.id, shadow: host.shadowRoot.activeElement && host.shadowRoot.activeElement.id}"),
    ("keys", K.TAB), ("snap", [])]

S["form-associated-custom-element"] = [
    ("html", '<x-face id="x" tabindex="0">face</x-face><button id="after">after</button>'),
    ("js", "if (!customElements.get('x-face')) customElements.define('x-face', class extends HTMLElement { static formAssociated = true; }); x.focus()"),
    ("snap", ["x"]),
    ("ajs", "x.setAttribute('disabled', ''); log.push('--disabled--'); await frames2()"), ("snap", ["x"]),
    ("js", "x.blur(); x.focus()"), ("snap", ["x"])]

S["popovertarget-button"] = [
    ("html", '<button id="b" popovertarget="p">open</button><div id="p" popover>pop</div>'),
    focus("b"), dis("b"), ("keys", K.ENTER), ("keys", K.SPACE), ("ajs", "await frames2()"),
    ("snap", ["b", "p"])]

S["commandfor-button"] = [
    ("html", '<button id="b" commandfor="p" command="show-popover">open</button><div id="p" popover>pop</div>'),
    focus("b"), dis("b"), ("keys", K.ENTER), ("keys", K.SPACE), ("ajs", "await frames2()"),
    ("snap", ["b", "p"])]

S["space-pagedown-scroll"] = [
    ("html", '<button id="b">b</button>'),
    focus("b"), dis("b"), ("keys", K.SPACE), ("ajs", "await frames2()"), ("snap", ["b"]),
    ("keys", K.PAGE_DOWN), ("ajs", "await frames2()"), ("snap", ["b"]),
    ("js", "scrollTo(0, 0)"), ("html", '<input id="t">'), focus("t"), dis("t"),
    ("keys", K.PAGE_DOWN), ("ajs", "await frames2()"), ("snap", ["t"])]

S["focus-other-and-blur"] = [
    ("html", '<button id="b">b</button><button id="o">o</button>'),
    focus("b"), dis("b"), ("js", "b.blur()"), ("snap", ["b"]),
    ("js", "b.disabled = false; b.focus()"), dis("b"), focus("o"), ("snap", ["b", "o"])]

S["click-elsewhere"] = [
    ("html", '<button id="b">b</button><p id="para" style="height:100px">text</p>'),
    focus("b"), dis("b"), ("click", "para"), ("snap", ["b"])]

S["focus-visible-kept"] = [
    ("html", '<button id="before">before</button><button id="b">b</button>'),
    focus("before"), ("keys", K.TAB), ("snap", ["b"]), dis("b"), ("snap", ["b"])]

S["file-color-pickers-keys"] = [
    ("html", '<input type="file" id="fi"><input type="color" id="co">'),
    focus("fi"), dis("fi"), ("keys", K.SPACE), ("keys", K.ENTER), ("sleep", 0.5), ("snap", ["fi"]),
    focus("co"), ("ajs", "await frames2()"), ("snap", ["co"]),
    ("js", "fi.disabled = false"), focus("co"), dis("co"), ("keys", K.SPACE), ("keys", K.ENTER),
    ("sleep", 0.5), ("snap", ["co"])]

S["disabled-then-hidden"] = [
    ("html", '<button id="b">b</button>'),
    focus("b"), dis("b"), ("ajs", "b.hidden = true; await frames2()"), ("snap", ["b"])]


def make_driver():
    kind, binary = sys.argv[1], sys.argv[2]
    if kind == "firefox":
        o = webdriver.FirefoxOptions()
        o.binary_location = binary
        o.add_argument("-headless")
        o.set_preference("dom.forms.retain_focus_on_disabled.enabled", sys.argv[3] == "on")
        return webdriver.Firefox(options=o)
    o = webdriver.ChromeOptions()
    o.binary_location = binary
    o.add_argument("--headless=new")
    return webdriver.Chrome(options=o, service=webdriver.ChromeService(sys.argv[3]))


def run(d, name, steps):
    d.get(URL)
    out = []
    for step in steps:
        kind = step[0]
        if kind == "html":
            d.execute_script("setup(arguments[0])", step[1])
        elif kind == "js":
            r = d.execute_script(step[1])
            if r is not None:
                out.append({"js": r})
        elif kind == "ajs":
            d.execute_async_script(f"const done = arguments[0]; (async () => {{ {step[1]} }})().then(() => done(), e => done(String(e)))")
        elif kind == "keys":
            ActionChains(d).send_keys(step[1]).perform()
            time.sleep(0.15)
        elif kind == "chord":
            ActionChains(d).key_down(step[1]).send_keys(step[2]).key_up(step[1]).perform()
            time.sleep(0.15)
        elif kind == "altdown":
            ActionChains(d).key_down(K.ALT).send_keys(K.ARROW_DOWN).key_up(K.ALT).perform()
            time.sleep(0.15)
        elif kind == "shifttab":
            ActionChains(d).key_down(K.SHIFT).send_keys(K.TAB).key_up(K.SHIFT).perform()
            time.sleep(0.15)
        elif kind == "click":
            d.find_element(By.ID, step[1]).click()
            time.sleep(0.15)
        elif kind == "sleep":
            time.sleep(step[1])
        elif kind == "snap":
            out.append(d.execute_script("return snap(arguments[0])", step[1]))
    return out


def main():
    d = make_driver()
    try:
        d.set_window_size(1000, 800)
        d.get(URL)
        print(json.dumps({"ua": d.execute_script("return navigator.userAgent")}), flush=True)
        only = set(sys.argv[4:])
        for name, steps in S.items():
            if only and name not in only:
                continue
            try:
                print(json.dumps({"name": name, "out": run(d, name, steps)}), flush=True)
            except Exception as e:  # noqa: BLE001
                print(json.dumps({"name": name, "error": str(e)[:300]}), flush=True)
    finally:
        d.quit()


main()
