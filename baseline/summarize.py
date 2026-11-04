"""Summarize run.py JSON lines compactly."""
import json
import sys

for line in open(sys.argv[1]):
    r = json.loads(line)
    if "ua" in r:
        print(r["ua"])
        continue
    if "error" in r:
        print(r["id"], r["how"], "ERROR", r["error"][:120])
        continue
    parts = [f'{r["id"]}/{r["how"]}']
    for k in ["before", "afterDisable", "type z", "space", "down", "enter", "tab"]:
        if k not in r:
            continue
        s = r[k]
        ev = ",".join(e for e in s["log"] if not e.startswith("keydown"))
        kd = [e for e in s["log"] if e.startswith("keydown")]
        bits = [f'act={s["active"]}']
        if k != "tab":
            bits.append(f'focus={int(s["focus"])}')
        for f in ["value", "checked", "selectedIndex", "open"]:
            if s[f] not in (None, False, ""):
                bits.append(f"{f}={s[f]}")
        if s["scrollY"]:
            bits.append(f'scroll={s["scrollY"]}')
        if kd:
            bits.append(kd[0])
        if ev:
            bits.append(f"ev=[{ev}]")
        parts.append(f"{k}: " + " ".join(bits))
    print("\n  ".join(parts))
