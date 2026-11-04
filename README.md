# Compat impact of keeping focus on controls that become disabled (whatwg/html#13170)

Proposed change: a focused form control that becomes disabled keeps focus (no focus fixup to the
viewport, no `blur`/`focusout`), can't be focused again while disabled, and doesn't perform
control-specific keyboard actions (editing, toggling, activation, implicit submission, opening
pickers); open pickers are dismissed. Today Chrome Canary, Safari TP and Firefox all move focus to
the body and fire `blur`/`focusout` (`baseline/`).

## Scope (agreed at kickoff, 2026-11-04)

- Implementation: Gecko bug 2087206 (two commits, cherry-picked onto `main` at dcafde486e11),
  behind `dom.forms.retain_focus_on_disabled.enabled`; before = pref off, after = pref on, same
  build, headless.
- Corpus: Common Crawl CC-MAIN-2026-39, the 12 local WARCs (seed 11397), inline scripts and
  inline event handler attributes only; HTTP Archive `sample_data.requests_10k` for external
  scripts. Query budget 0.5 TiB total, no full-crawl `response_body` queries.
- Live tests: ~30 static-pattern hits, benign keyboard interaction only (focus the control the
  page's handler is on, type, Enter twice); search, filter, carousel-like controls; never submit
  contact, signup, or chat forms.
- Also: extend local test pages to find Gecko implementation differences from the PR; draft, don't
  file.
- Run to the end (no early stop).

## Summary

Changing which element has focus is invisible to most pages. The one observable difference that
reached user-visible behavior: under the PR, key events keep going to the focused disabled control
and run its listeners. Previously they went to the body. A page whose Enter handler disables its
own input, with no re-entry guard, now repeats the action on a second Enter. That's rare
(0.0086% of Common Crawl pages, about 0.03% of HTTP Archive 10k-sample root pages per client),
and where testable the repeat was a duplicate search or a restarted navigation to the same URL. A
variant that sends key events to the body while the focused control is disabled (setup C) kept
focus and avoided every repeat seen.

Nothing in the reviewed code depends on `blur`/`focusout` firing, or on `activeElement` becoming
the body, when a focused control is disabled. Several modal focus traps and "refocus after
re-enable" helpers get better.

The two landed Gecko commits deviate from the PR in three ways: implicit submission from disabled
checkboxes and radios, arrow keys on a disabled radio, and an open `base-select` picker that stays
open. The rest of the patch series (D338542-D338545, not yet landed) fixes all three. Space no
longer scrolling from a disabled control remains either way; the PR doesn't say.

## 1. Common Crawl and HTTP Archive

Common Crawl CC-MAIN-2026-39, 12 WARCs (seed 11397), 255,716 HTML responses (all crawled URLs,
not only root pages); `scan_cc.py` reads inline scripts and inline handler attributes only.
Output: `out-cc/hits.jsonl` (its last line has the totals). A page counts when the code that
disables an element (`.disabled = true`, `prop('disabled', true)`, `attr('disabled', …)`,
`setAttribute('disabled', …)`) has the named pattern within 600 chars:

| Pattern | Pages | Groups reviewed |
|---|---|---|
| any disabling | 9,802 | |
| Enter-key check (`enter`) | 140 | all 61 |
| other key binding, no Enter check (`key`) | 398 | 40 of 229 (seeded) |
| `blur`/`focusout` binding (`blur`) | 166 | 30 of 80 (seeded) |
| `activeElement` (`active`) | 77 | all 25 |

`dossiers_cc.py` groups pages by a normalized snippet; the read-only reviewer agent classified each
group (verdicts in `out-cc/verdicts-*.csv`, spot-checked by hand).

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

The double-action groups: 18 pages repeat a search or restart the same navigation (12 of them are
one news site's search suggestions); 4 pages repeat a POST (a chat widget, a newsletter signup, two
music sites' comment boxes). The focus-loss-dependent group disables a quantity field for 1s on
Enter, apparently to make it lose focus; with the change it stays focused.

HTTP Archive `httparchive.sample_data.requests_10k`, root pages, script and HTML bodies
(`queries/sample10k_hits.sql`, output `queries/sample10k_hits.json`): 5,991 desktop and 7,203
mobile pages with such bodies. 4,645 and 5,380 disable something from script (mostly library
code). 24 and 24 have an Enter check within 600 chars before disabling, in 35 distinct bodies
(`out-ha/dossiers-enter/`, verdicts in `out-ha/verdicts-enter.csv`):

| Verdict | desktop pages | mobile pages |
|---|---|---|
| double-action | 2 | 2 |
| guarded | 2 | 3 |
| not-focused | 6 | 6 |
| unrelated | 12 | 14 |
| unclear | 2 | 1 |

The double-action pages are a bank's account-rename field (`keyup` Enter disables the field and
POSTs the same label again on a second Enter; it's behind login, so not live-tested) and
masutabe.info (nsfw) (a search box restarts the same navigation).

## 2. Live comparison

Same Firefox build, headless, 1366x900. `live/live.py`: setups A and A2 have the pref off (A2
measures page noise), B has it on. C has the pref on plus `live/variant.js`, which sends key events
to the body while the focused element is a disabled control. `live/preload.js` logs disabling of
the focused control, Enter keydown targets, fetch/XHR/form submission and `beforeunload`, with query
strings dropped. Each candidate: focus the control the page's handler is on, type, press Enter
twice. `live/sanity.html` checks each setup (A: one fetch; B: two; C: one with focus kept).

13 candidates (`live/candidates.jsonl`, search, filter, quantity and carousel controls; no
chat, comment or signup forms). 8 couldn't be tested: the control or carousel was gone from the
live page, or a bot challenge blocked the load. detik.com's search (3 runs) never disabled the input
in any setup, so the crawled code path wasn't hit. Results (`out-live/results.jsonl`, summary via
`live/summarize_live.py`):

| Page | A, A2 | B | C |
|---|---|---|---|
| prosol-farben.de search, second Enter 0.2s later | 1 search request; second Enter hits body | 2 search requests (second from the disabled input) | 1 request, focus kept |
| kamo.com search | 1 navigation | navigation restarted | 1 navigation |
| masutabe.info (nsfw) search | 1 navigation | navigation restarted | 1 navigation |

With a 1s gap, prosol-farben.de had already re-enabled the input. B's second search then came from
a focused, enabled input, which is the intended improvement (A needs a click back into the box).

## 3. Implementation differences (Gecko vs PR)

`impl/run_impl.py` runs 41 scenarios with real WebDriver key input against `impl/page.html`, with
the pref on and off (`impl/fx-on.jsonl`, `impl/fx-off.jsonl`, `impl/k-*.jsonl`; print with
`impl/show.py`). With the pref on, focus is kept for buttons, text-like inputs, textarea, select,
date/time, number, range, color, file, fieldset-disabled descendants, form-associated custom
elements, controls in iframes and in shadow trees. Tab/Shift+Tab move on and fire `blur`. The
control can't be refocused, and typing after re-enabling works without a new `focus` event. A pending
edit fires `change` on the later Tab, and user validity is kept. Disabled controls don't edit,
toggle, select, reset, submit, or open popovers/commands. Deviations from the PR:

- Enter on a focused disabled checkbox or radio still does implicit submission (`submit` fires).
  Fixed by D338542.
- ArrowDown/ArrowRight on a focused disabled radio moves focus to the next radio and checks it.
  Fixed by D338542.
- An open `appearance: base-select` picker stays open after its `select` is disabled (`:open`
  still matches); the PR hides it. Fixed by D338544.
- Space on a focused disabled button (or checkbox, select) no longer scrolls the page; PageDown
  still does. The PR doesn't say either way; before, focus was on the body, so Space scrolled.
  Unchanged with the full series.

`impl/fx-on-series.jsonl` reruns all scenarios with the rest of the series (D338542, D338543,
D338544, D338545 from Phabricator) applied on top. Only the three fixes above differ; key events
still go to the focused disabled control, so page key handlers on it still run (2 sends from 2
Enters in `keydown-self-disable-textarea`).

## 4. Why a second Enter repeats the page's action

Under the PR, the user agent must not perform control-specific keyboard actions on a focused
disabled control, but the key event is still fired. The PR's key event steps fire it at the
focused area's DOM anchor, which is the disabled control, and nothing in HTML stops dispatch to a
disabled form control (only click events from the user interaction task source are blocked). So
the control's own key listeners run, and the event bubbles from it. Before the change this
couldn't happen: focus had moved to the body, so later key events targeted the body.

The repeated action isn't a browser default action, so suppressing default actions on a disabled
target doesn't change it. The browser already doesn't activate the control:
`button-onclick-self-disable` gets 1 click from 2 Enters on the disabled button. In each live case,
the page's own key listener does the work: a jQuery `keyup` handler on the input
(prosol-farben.de), an inline key event handler attribute (kamo.com), and a `keypress` handler
delegated from `document` (masutabe.info). The same holds for the double-action groups in section 1.

The case is rare and mild (section 1), and it can be resolved in the spec; one option is below.

Gecko also fires key events at the disabled control.
`nsGenericHTMLFormElement::IsElementDisabledForEvents` (`dom/html/nsGenericHTMLElement.cpp`) returns
false for trusted `keydown`/`keypress`/`keyup` and focus events while
`dom.forms.always_allow_key_and_focus_events.enabled` is on (default true, bug 1818287). If that
pref is off, the switch falls through to the pointer-event case and still returns false while
`dom.forms.always_allow_pointer_events.enabled` is on (default true, bug 1799565). D338542 only
calls `preventDefault()` on keyboard events at a disabled input, which stops the browser's default
actions but not page listeners.

Blocking these events isn't a fix. With both prefs off (`impl/k-on-nokeyevents.jsonl`), the repeat
is gone, but the key event reaches no listener at all, not even on `document`. Focus events are
blocked too, so a later Tab fires no `blur`/`focusout`/`change` and user validity isn't kept.
It would also go against `html/semantics/disabled-elements/event-propagate-disabled-keyboard.tentative.html`,
which expects key events from focused descendants of disabled `fieldset`, `button` and
`delegatesFocus` form-associated custom elements to propagate.

What avoided the repeat in the live comparison (setup C) is retargeting. While the focused area's
DOM anchor is itself an actually disabled form control, fire key events at the body, as when
focus had moved there. Focus is kept, focus events and the later `change` still fire, and focused
descendants of disabled ancestors aren't affected. This needs a change to the PR's key event steps
as well as to Gecko. `live/variant.js` approximates it with a script and checks the event target
rather than the innermost focused element. That differs only for focus inside a disabled
`delegatesFocus` custom element, which none of the tested pages had.

## Not covered

Native pickers (headless can't show them); logged-in flows; mobile and soft keyboards; external
scripts beyond the HTTP Archive 10k sample; handlers that reach the disabling through a function
more than 600 chars away; other engines' implementations (none yet); and Safari TP/Chrome Canary
only as baselines (`baseline/`).

## Query bytes

| Query | Bytes processed |
|---|---|
| `queries/sample10k_hits.sql` (2026-11-04) | 73,219,512,166 (upper bound from dry run) |

## Reproduce

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
