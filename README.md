# Compat impact of keeping focus on controls that become disabled (whatwg/html#13170)

Proposed change: a focused form control that becomes disabled keeps focus (no focus fixup to the
viewport, no `blur`/`focusout`), can't be focused again while disabled, and doesn't perform
control-specific keyboard actions (editing, toggling, activation, implicit submission, opening
pickers); open pickers are dismissed. Today Chrome Canary, Safari TP and Firefox all move focus to
the body and fire `blur`/`focusout` (`baseline/`).

## Summary

Keeping focus is invisible to almost all pages. No reviewed code depends on `blur`/`focusout`
firing, or on `activeElement` becoming the body, when a focused control is disabled, and several
modal focus traps and "refocus after re-enable" helpers get better.

One difference reaches users. Under the PR, key events keep going to the focused disabled control,
so a page whose Enter handler disables its own input, with no re-entry guard, repeats its action on
a second Enter. That's rare (0.0086% of Common Crawl pages, about 0.03% of HTTP Archive 10k-sample
root pages per client), and where testable the repeat was a duplicate search or a restarted
navigation to the same URL. Sending key events to the body while the focused control itself is
disabled (setup C) keeps focus and avoided every repeat seen (section 1).

Gecko's two landed commits deviate from the PR in three ways, all fixed by the rest of the patch
series (not yet landed). Space no longer scrolling from a disabled control is a question for the
PR (section 4).

## Scope

- Implementation: Gecko bug 2087206 (two commits, cherry-picked onto `main` at dcafde486e11),
  behind `dom.forms.retain_focus_on_disabled.enabled`; before = pref off, after = pref on, same
  build, headless.
- Corpus: Common Crawl CC-MAIN-2026-39, the 12 local WARCs (seed 11397), inline scripts and inline
  event handler attributes only; HTTP Archive `sample_data.requests_10k` for external scripts.
  Query budget 0.5 TiB total, no full-crawl `response_body` queries.
- Live tests: ~30 static-pattern hits, benign keyboard input only (focus the control the page's
  handler is on, type, Enter twice) on search, filter and carousel-like controls; never submit
  contact, signup, or chat forms.
- Also: local test pages for Gecko differences from the PR; draft, don't file. Run to the end.

## 1. Why a second Enter repeats the page's action

The PR stops control-specific keyboard actions on a focused disabled control, but still fires the
key event at it: its key event steps target the focused area's DOM anchor, and HTML only blocks
click events from the user interaction task source at disabled form controls. So the control's own
key listeners run, and the event bubbles from it. Before, focus had moved to the body, which got
later key events.

The repeated action isn't a default action, so suppressing default actions on a disabled target
doesn't change it; the browser already doesn't activate the control (`button-onclick-self-disable`
gets 1 click from 2 Enters). In each live case the page's own listener does the work: a jQuery
`keyup` handler on the input (prosol-farben.de), an inline key event handler attribute (kamo.com),
and a `keypress` handler delegated from `document` (masutabe.info). The same holds for the crawl's
double-action groups.

Gecko matches the PR here. `nsGenericHTMLFormElement::IsElementDisabledForEvents`
(`dom/html/nsGenericHTMLElement.cpp`) allows trusted `keydown`/`keypress`/`keyup` and focus events
while `dom.forms.always_allow_key_and_focus_events.enabled` is on (default true, bug 1818287). With
it off, the switch falls through to the pointer-event case, which still allows them while
`dom.forms.always_allow_pointer_events.enabled` is on (default true, bug 1799565). D338542 only
calls `preventDefault()` on key events at a disabled input, which stops default actions, not page
listeners.

Blocking these events isn't a fix. With both prefs off (`impl/k-on-nokeyevents.jsonl`) the repeat
is gone, but the key event reaches no listener at all, not even on `document`. Focus events are
blocked too, so a later Tab fires no `blur`/`focusout`/`change` and user validity isn't kept. It
would also go against
`html/semantics/disabled-elements/event-propagate-disabled-keyboard.tentative.html`, which expects
key events from focused descendants of disabled `fieldset`, `button` and `delegatesFocus`
form-associated custom elements to propagate.

Retargeting avoids the repeat: while the focused area's DOM anchor is itself an actually disabled
form control, fire key events at the body, as when focus had moved there. Focus is kept, focus
events and the later `change` still fire, and focused descendants of disabled ancestors aren't
affected. It needs a change to the PR's key event steps (raised on whatwg/html#13159) and the
matching one in Gecko (bug 2087206). `live/variant.js` approximates it in script and checks the
event target rather than the innermost focused element; that differs only for focus inside a
disabled `delegatesFocus` custom element, which none of the tested pages had.

## 2. Common Crawl and HTTP Archive

Common Crawl CC-MAIN-2026-39, 12 WARCs (seed 11397), 255,716 HTML responses (all crawled URLs, not
only root pages). `scan_cc.py` reads inline scripts and inline handler attributes and counts a page
when code that disables an element (`.disabled = true`, `prop('disabled', true)`,
`attr('disabled', …)`, `setAttribute('disabled', …)`) has the pattern within 600 chars
(`out-cc/hits.jsonl`, totals on its last line). `dossiers_cc.py` groups pages by normalized
snippet; the read-only reviewer agent classified each group (`out-cc/verdicts-*.csv`, spot-checked
by hand).

| Pattern | Pages | Groups reviewed |
|---|---|---|
| any disabling | 9,802 | |
| Enter-key check (`enter`) | 140 | all 61 |
| other key binding, no Enter check (`key`) | 398 | 40 of 229 (seeded) |
| `blur`/`focusout` binding (`blur`) | 166 | 30 of 80 (seeded) |
| `activeElement` (`active`) | 77 | all 25 |

| Verdict | `enter` pages (groups) | `key` groups | `blur` groups | `active` groups |
|---|---|---|---|---|
| double-action | 22 (9) | 0 | | |
| guarded | 4 (2) | 0 | | |
| focus-loss-dependent | 1 (1) | 0 | 0 | 0 |
| improved | | | 0 | 1 |
| benign | | | 14 | 15 |
| not-focused | 46 (19) | 18 | 9 | 7 |
| unrelated | 63 (27) | 20 | 7 | 2 |
| unclear | 4 (3) | 2 | 0 | 0 |

Of the double-action pages, 18 repeat a search or restart the same navigation (12 are one news
site's search suggestions) and 4 repeat a POST (a chat widget, a newsletter signup, two music
sites' comment boxes). The focus-loss-dependent page disables a quantity field for 1s on Enter,
apparently to make it lose focus; with the change it stays focused.

HTTP Archive `httparchive.sample_data.requests_10k`, root pages, script and HTML bodies
(`queries/sample10k_hits.sql`, output `queries/sample10k_hits.json`): of 5,991 desktop and 7,203
mobile pages, 4,645 and 5,380 disable something from script (mostly library code), and 24 and 24
have an Enter check within 600 chars before disabling, in 35 distinct bodies
(`out-ha/dossiers-enter/`, `out-ha/verdicts-enter.csv`):

| Verdict | desktop pages | mobile pages |
|---|---|---|
| double-action | 2 | 2 |
| guarded | 2 | 3 |
| not-focused | 6 | 6 |
| unrelated | 12 | 14 |
| unclear | 2 | 1 |

The double-action pages are a bank's account-rename field (`keyup` Enter disables it and POSTs the
same label again on a second Enter; behind login, so not live-tested) and masutabe.info (nsfw) (a
search box restarts the same navigation).

## 3. Live comparison

Same Firefox build, headless, 1366x900 (`live/live.py`): A and A2 with the pref off (A2 measures
page noise), B with it on, C with it on plus `live/variant.js`. `live/preload.js` logs disabling of
the focused control, Enter keydown targets, fetch/XHR/form submission and `beforeunload`, with query
strings dropped. `live/sanity.html` checks each setup (A: one fetch; B: two; C: one with focus
kept).

Of 13 candidates (`live/candidates.jsonl`), 8 couldn't be tested (the control or carousel was gone,
or a bot challenge blocked the load), and detik.com's search never disabled the input in 3 runs.
Results (`out-live/results.jsonl`, `live/summarize_live.py`):

| Page | A, A2 | B | C |
|---|---|---|---|
| prosol-farben.de search, second Enter 0.2s later | 1 search request; second Enter hits body | 2 search requests (second from the disabled input) | 1 request, focus kept |
| kamo.com search | 1 navigation | navigation restarted | 1 navigation |
| masutabe.info (nsfw) search | 1 navigation | navigation restarted | 1 navigation |

With a 1s gap, prosol-farben.de had already re-enabled the input, so B's second search came from a
focused, enabled input: the intended improvement (A needs a click back into the box).

## 4. Gecko vs the PR

`impl/run_impl.py` runs 41 scenarios with real WebDriver key input against `impl/page.html`, pref
on and off (`impl/fx-on.jsonl`, `impl/fx-off.jsonl`, `impl/k-*.jsonl`; print with `impl/show.py`).
With the pref on, focus is kept for buttons, text-like inputs, textarea, select, date/time, number,
range, color, file, fieldset-disabled descendants, form-associated custom elements, and controls in
iframes and shadow trees. Tab/Shift+Tab move on and fire `blur`; the control can't be refocused;
typing after re-enabling works without a new `focus` event; a pending edit fires `change` on the
later Tab, and user validity is kept. Disabled controls don't edit, toggle, select, reset, submit,
or open popovers/commands.

`impl/fx-on-series.jsonl` reruns everything with the rest of the series (D338542, D338543, D338544,
D338545) applied. No difference needs a new Gecko bug:

- Enter on a focused disabled checkbox or radio still does implicit submission (`submit` fires),
  and ArrowDown/ArrowRight on a focused disabled radio moves focus to the next radio and checks it.
  Fixed by D338542, not yet landed.
- An open `appearance: base-select` picker stays open after its `select` is disabled (`:open` still
  matches); the PR hides it. Fixed by D338544, not yet landed.
- Space on a focused disabled button (or checkbox, select) no longer scrolls the page; PageDown
  still does. Before, focus was on the body, so Space scrolled. The PR doesn't say; a question for
  whatwg/html#13170. Unchanged with the series.
- Page key listeners on the focused disabled control still run (2 sends from 2 Enters in
  `keydown-self-disable-textarea`), as the PR says (section 1).

## Not covered

Native pickers (headless can't show them); logged-in flows; mobile and soft keyboards; external
scripts beyond the HTTP Archive 10k sample; handlers that reach the disabling through a function
more than 600 chars away; other engines' implementations (none yet); and Safari TP/Chrome Canary
only as baselines (`baseline/`).

## Query bytes

| Query | Bytes processed |
|---|---|
| `queries/sample10k_hits.sql` (2026-11-04) | 0.067 TiB (upper bound from dry run) |

## Reproduce

This run was done with the [`httparchive` skill](https://github.com/zcorpan/web-platform-skills/blob/main/docs/httparchive.md). The steps below are standalone and rerun the same analysis without the skill.

```sh
python3 -m venv .venv && .venv/bin/pip install selenium warcio
.venv/bin/python scan_cc.py out-cc/hits.jsonl ~/git/commoncrawl/cc-data/CC-MAIN-2026-39/*.warc.gz
.venv/bin/python dossiers_cc.py out-cc/hits.jsonl enter out-cc/dossiers-enter
bq query --use_legacy_sql=false --format=json --max_rows=100000 < queries/sample10k_hits.sql > queries/sample10k_hits.json
FX=<objdir>/dist/Nightly.app/Contents/MacOS/firefox  # mozilla/firefox main + bug 2087206
printf '{"id": "sanity", "url": "file://%s/live/sanity.html", "selector": "#q", "text": "hi", "wait": 1}\n' "$PWD" > live/sanity.jsonl
.venv/bin/python live/live.py "$FX" live/sanity.jsonl out-sanity A,B,C
.venv/bin/python live/live.py "$FX" live/candidates.jsonl out-live A,A2,B,C
.venv/bin/python impl/run_impl.py firefox "$FX" on > impl/fx-on.jsonl
.venv/bin/python baseline/run.py chrome "$CHROME_CANARY" "$CHROMEDRIVER" > baseline/chrome.jsonl
```

Live pages change, so a rerun won't match exactly. Screenshots (`out*/shots/`) aren't committed.
