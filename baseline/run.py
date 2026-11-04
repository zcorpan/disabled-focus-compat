"""Focus a control (script focus or click), disable it, then send keys. Prints JSON lines.

Usage: run.py firefox <binary> <pref on|off> | run.py chrome <binary> <chromedriver>
"""
import json
import pathlib
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

URL = pathlib.Path(__file__).with_name("test.html").as_uri()
IDS = ["button", "submit", "text", "textarea", "select", "multiple", "checkbox", "radio",
       "date", "number", "range", "fsbutton", "base"]
CLICK_IDS = ["select", "date", "base", "button", "text"]
KEYS = [("type z", "z"), ("space", Keys.SPACE), ("down", Keys.ARROW_DOWN),
        ("enter", Keys.ENTER), ("tab", Keys.TAB)]


def make_driver():
    kind, binary = sys.argv[1], sys.argv[2]
    if kind == "firefox":
        o = webdriver.FirefoxOptions()
        o.binary_location = binary
        o.add_argument("-headless")
        o.set_preference("dom.forms.retain_focus_on_disabled.enabled", sys.argv[3] == "on")
        return webdriver.Firefox(options=o)
    if kind == "safari":
        o = webdriver.SafariOptions()
        o.use_technology_preview = True
        return webdriver.Safari(options=o, service=webdriver.SafariService(executable_path=binary))
    o = webdriver.ChromeOptions()
    o.binary_location = binary
    o.add_argument("--headless=new")
    return webdriver.Chrome(options=o, service=webdriver.ChromeService(sys.argv[3]))


def state(d, id_):
    return d.execute_script("return state(arguments[0])", id_)


def case(d, id_, how):
    d.execute_script("reset()")
    el = d.find_element(By.ID, id_)
    if how == "click":
        el.click()
        time.sleep(0.3)
    else:
        d.execute_script("arguments[0].focus()", el)
    out = {"id": id_, "how": how, "before": state(d, id_)}
    d.execute_async_script("disable(arguments[0]).then(arguments[1])", id_)
    out["afterDisable"] = state(d, id_)
    for label, key in KEYS:
        if how == "click" and label != "tab":
            continue
        ActionChains(d).send_keys(key).perform()
        time.sleep(0.2)
        out[label] = state(d, id_)
    print(json.dumps(out), flush=True)


def main():
    d = make_driver()
    try:
        d.set_window_size(1000, 800)
        d.get(URL)
        print(json.dumps({"ua": d.execute_script("return navigator.userAgent")}), flush=True)
        for id_ in IDS:
            try:
                case(d, id_, "script")
            except Exception as e:  # noqa: BLE001
                print(json.dumps({"id": id_, "how": "script", "error": str(e)[:300]}), flush=True)
        for id_ in CLICK_IDS:
            try:
                case(d, id_, "click")
            except Exception as e:  # noqa: BLE001
                print(json.dumps({"id": id_, "how": "click", "error": str(e)[:300]}), flush=True)
    finally:
        d.quit()


main()
